import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from uuid import uuid4
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.efficiency import reply_plan,provider_limits,combine_usage
from agent.ensemble import EnsembleProvider
from agent.providers import LocalServerProvider,token_usage
from agent.server import create_app,ManagedStreamingResponse
from test_ensemble import fixture_config


class BudgetProvider:
    def __init__(self,settings):
        self.settings=settings;self.calls=[];self.last_usage=None;self.fail=False
    def stream(self,messages,cancel):
        self.calls.append({'settings':self.settings,'messages':copy.deepcopy(messages)})
        self.last_usage=None
        yield 'A concise ',messages
        if self.fail:raise RuntimeError('private failure detail')
        yield 'answer.',messages
        self.last_usage=token_usage(50,4,'fixture-tokenizer','stop')
    def generate(self,messages):
        self.calls.append({'settings':self.settings,'messages':copy.deepcopy(messages)})
        self.last_usage=token_usage(50,4,'fixture-tokenizer','stop')
        return 'A concise answer.',messages


class EfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.settings=Settings(provider='huggingface',data_dir=self.tmp.name,max_new_tokens=256,fast_max_new_tokens=96,reply_style='auto')
        self.provider=BudgetProvider(self.settings);self.agent=Agent(self.settings,self.provider)

    def test_auto_budgets_preserve_code_and_full_requests_and_operator_caps(self):
        for text in ['Hello','What is evaporation?']:
            self.assertEqual(reply_plan(self.settings,text,'fast').max_new_tokens,96)
        for text in ['Write a Python function','Give a detailed explanation','x'*601]:
            self.assertEqual(reply_plan(self.settings,text,'fast').max_new_tokens,256)
        self.assertEqual(reply_plan(self.settings,'Hello','thorough').max_new_tokens,256)
        self.assertEqual(reply_plan(replace(self.settings,max_new_tokens=20),'Hello','fast').max_new_tokens,20)
        self.assertEqual(reply_plan(self.settings,'Write a function','fast','brief').max_new_tokens,96)
        with self.assertRaises(ValueError):reply_plan(self.settings,'Hi','fast','invalid')

    def test_bounded_history_keeps_latest_pairs_and_current_question_without_deleting_saved_turns(self):
        session=str(uuid4())
        for i in range(8):self.agent.store.add(session,'Question '+str(i),'Answer '+str(i),[],self.settings.model)
        result=self.agent.answer('What now?',session)
        used=self.provider.calls[-1]['messages']
        self.assertEqual(len(used),10);self.assertEqual(used[1]['content'],'Question 4');self.assertEqual(used[-1]['content'],'What now?')
        self.assertEqual(len(self.agent.store.history(session,100)),9)
        self.assertEqual(result['performance']['history_turns_sent'],4)
        self.assertEqual(self.provider.settings.max_new_tokens,256)

    def test_usage_persists_but_private_text_does_not_enter_performance_records(self):
        session=str(uuid4());result=self.agent.answer('Confidential project fixture',session,user_id='private-user')
        performance=result['performance'];self.assertEqual(performance['usage']['output_tokens'],4)
        self.assertEqual(self.agent.store.history(session)[0]['performance'],performance)
        with self.agent.store.connect() as db:
            metadata=json.dumps(dict(db.execute('SELECT * FROM generation_metrics').fetchone()))
        self.assertNotIn('Confidential',metadata);self.assertNotIn('concise answer',metadata)
        self.assertEqual(self.agent.monitor.summary('other-user')['requests'],0)
        self.assertEqual(self.agent.monitor.summary('private-user')['reported_output_tokens'],4)
        self.agent.store.delete_session(session);self.assertEqual(self.agent.monitor.summary('private-user')['requests'],0)

    def test_cancel_failure_and_budget_restoration_do_not_save_partial_turns(self):
        session=str(uuid4());stream=self.agent.stream_answer('Hello',session,user_id='fixture')
        next(stream);next(stream);self.assertEqual(self.provider.settings.max_new_tokens,96);stream.close()
        self.assertEqual(self.provider.settings.max_new_tokens,256);self.assertFalse(self.agent.lock.locked())
        self.assertEqual(self.agent.store.history(session),[])
        self.assertEqual(self.agent.monitor.summary('fixture')['cancelled'],1)
        self.provider.fail=True
        with self.assertRaises(RuntimeError):self.agent.answer('Hello',session,user_id='fixture')
        self.assertEqual(self.agent.monitor.summary('fixture')['failed'],1);self.assertEqual(self.provider.settings.max_new_tokens,256)

    def test_fast_and_thorough_reuse_cached_weights_with_different_budgets_and_sum_usage(self):
        children=[]
        def factory(settings):
            child=BudgetProvider(settings);children.append(child);return child
        config=fixture_config();config['max_cached_models']=3
        team=EnsembleProvider(self.settings,config=config,provider_factory=factory)
        agent=Agent(self.settings,team,store=self.agent.store)
        fast=agent.answer('Hello',str(uuid4()));self.assertEqual(fast['performance']['usage']['model_calls'],1)
        child=children[0];self.assertEqual(child.calls[-1]['settings'].max_new_tokens,96)
        full=agent.answer('Hello again',str(uuid4()),response_mode='thorough')
        self.assertEqual(full['performance']['usage']['model_calls'],4)
        self.assertEqual(full['performance']['usage']['output_tokens'],16)
        self.assertEqual(child.calls[-1]['settings'].max_new_tokens,256)
        self.assertEqual(sum(provider is child for provider in team.providers.values()),1)
        self.assertEqual(len(children),3)
        self.assertIsNone(combine_usage([{'status':'failed'},{'status':'ok','usage':token_usage(2,3)}])['output_tokens'])

    def test_local_stream_usage_and_length_reason_are_taken_from_provider_not_estimated(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.is_redirect=False
        response.iter_lines.return_value=iter([b'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
            b'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":2}}',b'data: [DONE]'])
        from threading import Event
        provider=LocalServerProvider(replace(self.settings,provider='localserver'))
        with patch('agent.providers.requests.post',return_value=response) as post:
            text=''.join(chunk for chunk,_ in provider.stream([{'role':'system','content':'System'},{'role':'user','content':'Hello'}],Event()))
        self.assertEqual(text,'Hi');self.assertEqual(provider.last_usage['total_tokens'],14)
        self.assertEqual(provider.last_usage['finish_reason'],'length')
        self.assertNotIn('headers',post.call_args.kwargs)
        self.assertIsNone(token_usage(None,None)['total_tokens'])

    def test_http_send_disconnect_closes_iterator_and_releases_model(self):
        import anyio
        from starlette.requests import ClientDisconnect
        stream=self.agent.stream_answer('Hello',str(uuid4()),user_id='fixture')
        async def body():
            for event in stream:yield json.dumps(event)
        async def run():
            async def send(message):
                if message.get('body',b'').find(b'"delta"')>=0:raise OSError('Client left')
            async def receive():return {'type':'http.disconnect'}
            response=ManagedStreamingResponse(body(),close_stream=stream.close,media_type='text/event-stream')
            with self.assertRaises(ClientDisconnect):await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        anyio.run(run)
        self.assertFalse(self.agent.lock.locked());self.assertEqual(self.provider.settings.max_new_tokens,256)
        self.assertEqual(self.agent.monitor.summary('fixture')['cancelled'],1)

    def test_monitor_retention_and_like_configuration_latency_signal(self):
        perf={'response_mode':'fast','reply_style':'auto','elapsed_ms':100,'first_text_ms':30,'usage':token_usage(10,10)}
        for i in range(40):
            self.agent.monitor.record(self.settings,'fixture',str(uuid4()),'completed',{**perf,'elapsed_ms':100 if i<20 else 200},'model')
        summary=self.agent.monitor.summary('fixture');self.assertEqual(summary['signals'][0]['ratio'],2)
        with self.agent.store.connect() as db:
            record=db.execute('SELECT * FROM generation_metrics LIMIT 1').fetchone()
            columns=[key for key in record.keys() if key!='id'];values=[record[key] for key in columns]
            db.executemany('INSERT INTO generation_metrics ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',[values]*1001)
        self.agent.monitor.record(self.settings,'fixture','session','completed',perf,'model')
        with self.agent.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM generation_metrics').fetchone()[0],1000)

    def test_system_components_and_metrics_obey_account_and_owner_boundaries(self):
        app=create_app(replace(self.settings,api_token='a'*40),self.agent);alice=TestClient(app);bob=TestClient(app)
        headers={'Authorization':'Bearer '+'a'*40};payload={'username':'alice','display_name':'Alice','password':'local fixture password'}
        self.assertEqual(alice.get('/api/system').status_code,401)
        self.assertEqual(alice.get('/api/metrics',headers=headers).status_code,401)
        alice.post('/api/account/register',json=payload,headers=headers)
        bob.post('/api/account/register',json={**payload,'username':'bobby'},headers=headers)
        alice.post('/api/memories',json={'content':'Private account memory'},headers=headers)
        result=alice.get('/api/system',headers=headers).json()
        self.assertEqual([row['id'] for row in result['components']],['model','harness','context','infrastructure','governance'])
        self.assertNotIn('Private account memory',json.dumps(result))
        alice.post('/api/chat',json={'session_id':str(uuid4()),'message':'Hello'},headers=headers)
        self.assertEqual(alice.get('/api/metrics',headers=headers).json()['completed'],1)
        self.assertEqual(bob.get('/api/metrics',headers=headers).json()['completed'],0)
        self.assertEqual(alice.get('/api/admin/metrics',headers=headers).status_code,403)
        codefile=Path(self.tmp.name)/'owner.txt';self.agent.admin.initialize('alice',codefile)
        alice.post('/api/admin/unlock',json={'code':codefile.read_text().strip()},headers=headers)
        self.assertEqual(alice.get('/api/admin/metrics',headers=headers).json()['scope'],'server')
        alice.post('/api/admin/lock',headers=headers)
        self.assertEqual(alice.get('/api/admin/metrics',headers=headers).status_code,403)


if __name__=='__main__':unittest.main()
