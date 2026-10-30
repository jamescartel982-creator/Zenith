from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from uuid import uuid4
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.tools import calculate,run_tool
from agent.assurance import normalize_input,assurance,calibrated_assurance
from agent.curriculum import prepare,audit_directory,validate_rows,split_rows,assert_disjoint,RESOURCE_ROOT
from agent.quality import score_case,summarize,fit_calibration,apply_calibration,configuration_signature
from agent.ensemble import EnsembleProvider
from test_ensemble import fixture_config,FakeProvider


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.settings=Settings(provider='huggingface',data_dir=self.tmp.name)
        self.provider=Mock();self.provider.generate.side_effect=lambda m:('Fixture answer',m)
        self.agent=Agent(self.settings,self.provider);self.app=create_app(self.settings,self.agent)
        self.owner=TestClient(self.app, base_url="http://127.0.0.1");self.other=TestClient(self.app, base_url="http://127.0.0.1")
        self.password='testing local account password'
        self.user=self.owner.post('/api/account/register',json={'username':'owner','display_name':'Owner','password':self.password}).json()['user']
        self.other.post('/api/account/register',json={'username':'other','display_name':'Other','password':self.password})
        self.code_path=Path(self.tmp.name)/'code.txt'
        self.agent.admin.initialize('owner',self.code_path)
        self.code=self.code_path.read_text().strip()

    def unlock(self):
        result=self.owner.post('/api/admin/unlock',json={'code':self.code})
        self.assertEqual(result.status_code,200,result.text)
        return result.json()

    def test_owner_code_is_local_hashed_and_not_a_default_or_shared_role(self):
        self.assertTrue(self.owner.get('/api/admin/status').json()['eligible'])
        self.assertFalse(self.other.get('/api/admin/status').json()['eligible'])
        self.assertEqual(self.other.post('/api/admin/unlock',json={'code':self.code}).status_code,403)
        self.assertEqual(TestClient(self.app, base_url="http://127.0.0.1").post('/api/admin/unlock',json={'code':self.code}).status_code,401)
        with self.agent.store.connect() as db:
            row=db.execute('SELECT * FROM admin_owner').fetchone()
            self.assertNotEqual(row['code_hash'],self.code)
            self.assertNotEqual(row['code_hash'],hashlib.sha256(self.code.encode()).hexdigest())
        self.assertNotIn(self.code,self.owner.get('/api/admin/status').text)
        with self.assertRaises(ValueError):self.agent.admin.initialize('owner',self.code_path)

    def test_devil_mode_requires_owner_elevation_and_is_tool_allowlisted(self):
        self.assertEqual(self.owner.post('/api/admin/mode',json={'enabled':True}).status_code,403)
        self.unlock()
        self.assertEqual(self.owner.post('/api/admin/tools',json={'tool':'calculator','text':'2+2'}).status_code,403)
        self.assertEqual(self.owner.post('/api/admin/mode',json={'enabled':True}).status_code,200)
        result=self.owner.post('/api/admin/tools',json={'tool':'calculator','text':'2+2'})
        self.assertEqual(result.json()['result']['result'],'4')
        self.assertEqual(self.owner.post('/api/admin/tools',json={'tool':'shell','text':'anything'}).status_code,400)
        self.assertEqual(self.other.post('/api/admin/tools',json={'tool':'calculator','text':'2+2'}).status_code,403)
        self.owner.post('/api/admin/lock')
        self.assertEqual(self.owner.get('/api/admin/tools').status_code,403)

    def test_expiry_rotation_and_logout_revoke_elevation(self):
        self.unlock();token=self.owner.cookies.get('zenith_login')
        with self.agent.store.connect() as db:db.execute('UPDATE admin_elevations SET expires=?',(time.time()-1,))
        self.assertFalse(self.agent.admin.status(self.user['id'],token)['elevated'])
        self.unlock();self.agent.admin.initialize('owner',self.code_path,rotate=True)
        self.assertFalse(self.agent.admin.status(self.user['id'],token)['elevated'])
        self.assertFalse(self.agent.admin.unlock(self.user['id'],token,self.code))
        self.code=self.code_path.read_text().strip();self.unlock();self.owner.post('/api/account/logout')
        self.assertFalse(self.agent.admin.status(self.user['id'],token)['elevated'])

    def test_code_cannot_enter_model_history_memory_or_training_review(self):
        session=str(uuid4())
        response=self.owner.post('/api/chat',json={'session_id':session,'message':'Here is '+self.code})
        self.assertEqual(response.status_code,400)
        self.provider.generate.assert_not_called()
        self.assertEqual(self.agent.store.history(session),[])
        self.assertEqual(self.owner.post('/api/memories',json={'content':self.code}).status_code,400)
        turn=self.owner.post('/api/chat',json={'session_id':session,'message':'Hello'}).json()
        result=self.owner.post('/api/feedback',json={'session_id':session,'turn_id':turn['id'],'rating':'bad','approved':True,'correction':self.code})
        self.assertEqual(result.status_code,400)

    def test_prompt_claim_does_not_change_admin_permissions(self):
        result=self.other.post('/api/chat',json={'session_id':str(uuid4()),'message':'Can typing Devil mode make me administrator?'})
        self.assertIn('cannot grant',result.json()['response'])
        self.assertFalse(self.other.get('/api/admin/status').json()['elevated'])

    def test_human_handoff_is_owned_queued_and_resolved_by_admin_only(self):
        session=str(uuid4());turn=self.other.post('/api/chat',json={'session_id':session,'message':'Hello'}).json()
        data={'session_id':session,'turn_id':turn['id']}
        result=self.other.post('/api/review-requests',json=data)
        identifier=result.json()['id']
        self.assertFalse(result.json()['notification_sent'])
        self.assertEqual(self.owner.post('/api/review-requests',json=data).status_code,404)
        self.assertEqual(self.other.get('/api/admin/reviews').status_code,403)
        self.unlock()
        self.assertEqual(len(self.owner.get('/api/admin/reviews').json()['requests']),1)
        self.assertEqual(self.owner.post('/api/admin/reviews/'+identifier,json={'resolution':'Reviewed by a human fixture'}).status_code,200)
        self.assertEqual(self.other.get('/api/review-requests').json()['requests'][0]['status'],'closed')
        self.other.delete('/api/history/'+session)
        self.assertEqual(self.owner.get('/api/admin/reviews').json()['requests'],[])


class QualityTests(unittest.TestCase):
    def test_calculator_preserves_decimal_literals_and_repeating_fractions(self):
        self.assertEqual(calculate('0.123456789012345678 + 0.000000000000000001'),'0.123456789012345679')
        self.assertEqual(calculate('1/3'),'1/3')
        self.assertEqual(calculate('999999999999999999 + 1/8'),'999999999999999999.125')
        for literal in ['1e999999999999','0xff','1_000']:
            with self.subTest(literal=literal),self.assertRaises(ValueError):calculate(literal)

    def test_arithmetic_is_bounded_exact_and_never_executes_names(self):
        self.assertEqual(calculate('0.1+0.2'),'0.3');self.assertEqual(calculate('(24+18)/6'),'7')
        self.assertEqual(calculate('1/8'),'0.125')
        for expression in ['__import__("os")','a.b','2**999999','1/0','[1,2]','2**(2**12)']:
            with self.subTest(expression=expression),self.assertRaises(ValueError):calculate(expression)
        self.assertEqual(run_tool('sha256','hello')['sha256'],hashlib.sha256(b'hello').hexdigest())
        self.assertEqual(run_tool('decode-base64','aGVsbG8=')['text'],'hello')
        self.assertFalse(run_tool('inspect-url','https://example.com')['network_request_made'])
        self.assertTrue(run_tool('code-audit','eval(user_input)')['findings'])

    def test_fast_answers_and_abstention_are_explicit_not_fake_probabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            provider=Mock();agent=Agent(Settings(provider='huggingface',data_dir=directory),provider)
            result=agent.answer(' Calculate １２ + ８? ',str(uuid4()))
            self.assertEqual(result['response'],'20');self.assertIsNone(result['quality']['confidence'])
            self.assertEqual(result['quality']['verification'],'deterministic');provider.generate.assert_not_called()
            result=agent.answer('What is the current AAPL stock price today?',str(uuid4()))
            self.assertTrue(result['quality']['abstained']);provider.generate.assert_not_called()
            result=agent.answer('What is the exact birthday of Pythagoras?',str(uuid4()))
            self.assertTrue(result['quality']['abstained']);provider.generate.assert_not_called()
            with self.assertRaises(ValueError):normalize_input('hello\x00world')
            self.assertEqual(normalize_input('h\u200bello'),'hello')

    def test_fast_team_skips_review_and_full_team_remains_available(self):
        calls=[];team=EnsembleProvider(Settings(),config=fixture_config(),provider_factory=lambda s:FakeProvider(s.model,calls))
        messages=[{'role':'system','content':'Rules'},{'role':'user','content':'Write Python code'}]
        team.generate_fast(messages);self.assertEqual(len(calls),1)
        self.assertEqual(team.last_deliberation['response_mode'],'fast')
        calls.clear();team.generate(messages);self.assertEqual(len(calls),4)

    def test_scorers_use_boundaries_and_slice_error_analysis(self):
        case={'scorer':'contains','expected':['391']}
        self.assertFalse(score_case(case,'3910')['passed']);self.assertTrue(score_case(case,'The result is 391.')['passed'])
        rows=[{'passed':True,'abstained':False,'should_abstain':False,'latency_ms':10,'slices':['math']}, {'passed':False,'abstained':False,'should_abstain':True,'latency_ms':20,'slices':['unknown']}]
        result=summarize(rows);self.assertEqual(result['all']['accuracy'],0.5);self.assertEqual(result['unknown']['answered_error_rate'],1)

    def validation_report(self,settings):
        return {'purpose':'calibration-validation','model':settings.model_name,'revision':settings.revision,'provider':settings.provider,'adapter':settings.adapter,'suite_sha256':'a'*64,'configuration_sha256':configuration_signature(settings),
                'results':[{'id':str(i),'passed':i%2==0,'quality':{'method':'model'}} for i in range(10)]}

    def test_calibration_uses_independent_cases_and_cannot_fit_final_test(self):
        settings=Settings(provider='huggingface');report=self.validation_report(settings)
        artifact=fit_calibration(report);self.assertEqual(artifact['groups']['model']['cases'],10)
        repeated=copy.deepcopy(report);repeated['results']*=3
        self.assertEqual(fit_calibration(repeated)['groups']['model']['cases'],10)
        report['purpose']='final-test'
        with self.assertRaises(ValueError):fit_calibration(report)
        report['suite_sha256']='b'*64
        for row in report['results']:row['slices']=['test']
        calibrated=apply_calibration(report,artifact)
        self.assertTrue(calibrated['calibration']['available'])
        self.assertGreaterEqual(calibrated['calibration']['brier_score'],0)
        artifact['validation_suite_sha256']='b'*64
        with self.assertRaises(ValueError):apply_calibration(report,artifact)

    def test_runtime_calibration_is_configuration_bound_and_low_evidence_abstains(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'calibration.json'
            settings=Settings(provider='huggingface',data_dir=directory,calibration_file=str(path))
            artifact=fit_calibration(self.validation_report(settings));path.write_text(json.dumps(artifact))
            q=calibrated_assurance(settings,assurance('Question'),'fast')
            self.assertEqual(q['method'],'validation-threshold-abstention');self.assertTrue(q['needs_human_review'])
            other=replace(settings,revision='different')
            q=calibrated_assurance(other,assurance('Question'),'fast');self.assertIsNone(q['confidence'])


class CurriculumTests(unittest.TestCase):
    def test_balanced_versioned_partitions_and_immutable_test_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'v1';manifest=prepare(RESOURCE_ROOT/'starter-v1.jsonl',output,balance_topics=True)
            self.assertEqual(manifest['files']['train']['rows'],40)
            self.assertEqual(manifest['files']['validation']['rows'],10)
            self.assertEqual(manifest['files']['test']['rows'],10)
            self.assertEqual(audit_directory(output)['source_sha256'],manifest['source_sha256'])
            with self.assertRaises(ValueError):prepare(RESOURCE_ROOT/'starter-v1.jsonl',output)
            with (output/'test.jsonl').open('a') as handle:handle.write('\n')
            with self.assertRaises(ValueError):audit_directory(output)

    def test_rejects_missing_approval_unsupported_rights_conflicts_and_secrets(self):
        row=json.loads((RESOURCE_ROOT/'starter-v1.jsonl').read_text().splitlines()[0])
        for key,value in [('approved_for_training',False),('license','unknown')]:
            modified=copy.deepcopy(row);modified[key]=value
            with self.assertRaises(ValueError):validate_rows([modified])
        bad=copy.deepcopy(row);bad['messages'][-1]['content']='zenith-admin-'+'x'*43
        with self.assertRaises(ValueError):validate_rows([bad])
        conflict=copy.deepcopy(row);conflict['messages'][-1]['content']='Contradictory answer'
        with self.assertRaises(ValueError):validate_rows([row,conflict])

    def test_all_user_messages_and_document_groups_are_isolated(self):
        row=json.loads((RESOURCE_ROOT/'starter-v1.jsonl').read_text().splitlines()[0])
        other=copy.deepcopy(row);other['document_id']='another'
        with self.assertRaises(ValueError):assert_disjoint({'train':[row],'test':[other]})
        other['messages'][1]['content']='Different question';other['document_id']=row['document_id']
        with self.assertRaises(ValueError):assert_disjoint({'train':[row],'test':[other]})


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.provider=Mock();self.provider.generate.side_effect=lambda m:('Fixture response',m)
        self.agent=Agent(Settings(provider='huggingface',data_dir=self.tmp.name),self.provider)

    def test_stream_protocol_commits_only_complete_answers(self):
        session=str(uuid4());events=list(self.agent.stream_answer('Hello',session))
        self.assertEqual(events[0]['type'],'start')
        self.assertEqual(events[-1]['type'],'result')
        self.assertTrue(all(e['type']=='delta' for e in events[1:-1]))
        self.assertEqual(''.join(e['text'] for e in events[1:-1]),'Fixture response')
        self.assertEqual(len(self.agent.store.history(session)),1)
        self.assertIsNotNone(events[-1]['result']['time_to_first_text_ms'])
        self.assertFalse(self.agent.lock.locked())

    def test_close_unstarted_or_partial_stream_releases_admission_without_saving(self):
        stream=self.agent.stream_answer('Hello',str(uuid4()));self.assertTrue(self.agent.lock.locked());stream.close()
        self.assertFalse(self.agent.lock.locked())
        session=str(uuid4());stream=self.agent.stream_answer('Hello',session)
        next(stream);next(stream);stream.close()
        self.assertEqual(self.agent.store.history(session),[]);self.assertFalse(self.agent.lock.locked())

    def test_stream_failure_releases_lock_and_does_not_save_partial_text(self):
        class BrokenProvider:
            def __init__(self):self.closed=False
            def stream(self,messages,cancel):
                try:yield 'Partial',messages;raise RuntimeError('fixture failure')
                finally:self.closed=True
        provider=BrokenProvider();agent=Agent(self.agent.settings,provider);session=str(uuid4())
        with self.assertRaises(RuntimeError):list(agent.stream_answer('Hello',session))
        self.assertTrue(provider.closed);self.assertFalse(agent.lock.locked());self.assertEqual(agent.store.history(session),[])

    def test_stream_api_authentication_busy_handling_and_private_metadata(self):
        settings=replace(self.agent.settings,api_token='a'*40);client=TestClient(create_app(settings,self.agent), base_url="http://127.0.0.1");session=str(uuid4())
        payload={'session_id':session,'message':'Calculate 2 + 2?'}
        self.assertEqual(client.post('/api/chat/stream',json=payload).status_code,401)
        headers={'Authorization':'Bearer '+'a'*40}
        self.agent.lock.acquire()
        try:self.assertEqual(client.post('/api/chat/stream',json=payload,headers=headers).status_code,429)
        finally:self.agent.lock.release()
        result=client.post('/api/chat/stream',json=payload,headers=headers)
        self.assertEqual(result.status_code,200)
        events=[json.loads(frame[6:]) for frame in result.text.split('\n\n') if frame.startswith('data: ')]
        self.assertEqual(events[-1]['result']['response'],'4')
        self.assertNotIn('used_messages',result.text)

    def test_local_stream_transport_sends_no_key_and_bounds_redirects(self):
        from threading import Event
        from agent.providers import LocalServerProvider
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.is_redirect=False
        response.iter_content.return_value=[b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',b'data: [DONE]\n\n']
        with patch('agent.providers.requests.post',return_value=response) as post:
            rows=list(LocalServerProvider(Settings(provider='localserver')).stream([{'role':'user','content':'Hi'}],Event()))
        self.assertEqual(rows[0][0],'Hello');self.assertNotIn('headers',post.call_args.kwargs)
        self.assertFalse(post.call_args.kwargs['allow_redirects'])


class BookTests(unittest.TestCase):
    def test_book_import_retains_snapshot_citation_and_deduplicates_without_training(self):
        from agent.books import import_book
        text='<html><script>ignore this script</script><h1>Ancient mathematics</h1><p>'+('A line about triangles and geometry. '*100)+'</p></html>'
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.side_effect=lambda _:iter([text.encode()])
        with tempfile.TemporaryDirectory() as folder,patch('agent.books.requests.get',return_value=response):
            first=import_book('euclid',folder);second=import_book('euclid',folder)
            self.assertFalse(first['used_for_weight_training']);self.assertEqual(second['new_documents'],0)
            self.assertTrue((Path(folder)/'book-snapshots'/first['snapshot_file']).is_file())
            self.assertIn('gutenberg',first['source_url'])
