"""Local adversarial HTTP, credential, database and owner-boundary regressions."""
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from agent.browser_access import COOKIE, issue, valid, LIFETIME
from agent.config import Settings
from agent.core import Agent
from agent.owner_mfa import local_key
from agent.redaction import Redactor, RedactingStream
from agent.server import create_app
from agent.setup import write_configuration
from agent.storage import Store


class BrowserGrantTests(unittest.TestCase):
    def test_grants_expire_rotate_and_reject_tampering_without_containing_api_key(self):
        key=secrets.token_urlsafe(32);grant=issue(key,now=1000)
        self.assertNotIn(key,grant)
        self.assertTrue(valid(grant,key,now=1001))
        self.assertFalse(valid(grant,key,now=1000+LIFETIME))
        self.assertFalse(valid(grant,key,now=999))
        self.assertFalse(valid(grant,key+'rotated',now=1001))
        self.assertFalse(valid(grant[:-1]+('0' if grant[-1]!='0' else '1'),key,now=1001))
        self.assertFalse(valid('x'*10000,key,now=1001))


class HTTPHardeningTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.folder=Path(folder.name)
        self.key=secrets.token_urlsafe(32)
        self.settings=replace(Settings(),provider='huggingface',data_dir=folder.name,api_token=self.key)
        self.provider=Mock();self.provider.generate.side_effect=lambda messages:('Fixture answer.',messages)
        self.agent=Agent(self.settings,self.provider);self.app=create_app(self.settings,self.agent)
        self.client=TestClient(self.app,base_url='https://127.0.0.1')

    def headers(self,response,secure=True):
        self.assertEqual(response.headers['x-frame-options'],'DENY')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertIn("object-src 'none'",response.headers['content-security-policy'])
        self.assertIn("form-action 'self'",response.headers['content-security-policy'])
        self.assertEqual(response.headers['cross-origin-opener-policy'],'same-origin')
        self.assertIn('camera=()',response.headers['permissions-policy'])
        self.assertEqual('strict-transport-security' in response.headers,secure)

    def connect(self,client=None):
        client=client or self.client
        response=client.post('/api/access',json={'token':self.key})
        self.assertEqual(response.status_code,200,response.text)
        return response

    def register(self,client,name):
        self.connect(client)
        response=client.post('/api/account/register',json={'username':name,'display_name':name,'password':'temporary isolated test password'})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['user']

    def test_headers_cover_auth_origin_host_validation_missing_routes_and_exceptions(self):
        @self.app.get('/_test_failure')
        def failure():raise RuntimeError('internal '+self.key)
        cases=[self.client.get('/'),self.client.get('/api/account'),
               self.client.post('/api/account/logout',headers={'Origin':'https://foreign.invalid'}),
               self.client.get('/api/account',headers={'Host':'foreign.invalid'}),
               self.client.post('/api/access',json={'token':'x'*5000}),
               self.client.get('/missing'),self.client.get('/_test_failure')]
        self.assertEqual([r.status_code for r in cases],[200,401,403,400,422,404,500])
        for response in cases:
            self.headers(response);self.assertNotIn(self.key,response.text)
        local=TestClient(self.app,base_url='http://127.0.0.1')
        self.headers(local.get('/'),secure=False)

    def test_browser_grant_is_httponly_host_only_and_native_bearer_remains_compatible(self):
        response=self.connect();cookie=response.headers['set-cookie']
        for flag in ('HttpOnly','Secure','SameSite=strict','Path=/'):self.assertIn(flag,cookie)
        self.assertNotIn('Domain=',cookie);self.assertNotIn(self.key,cookie);self.assertNotIn(self.key,response.text)
        self.assertEqual(self.client.get('/api/account').status_code,200)
        self.assertEqual(self.client.get('/api/account',headers={'Authorization':'Bearer wrong'}).status_code,401)
        native=TestClient(self.app,base_url='https://127.0.0.1')
        self.assertEqual(native.get('/api/account',headers={'Authorization':'Bearer '+self.key}).status_code,200)

    def test_cross_origin_cookie_exchange_and_forged_owner_flags_do_not_grant_access(self):
        for origins in ({'Origin':'null'},{'Origin':'https://foreign.invalid'},
                        [('Origin','https://127.0.0.1'),('Origin','https://foreign.invalid')]):
            response=self.client.post('/api/access',json={'token':self.key},headers=origins)
            self.assertEqual(response.status_code,403)
        self.assertEqual(self.client.get('/api/account').status_code,401)
        self.register(self.client,'reader')
        self.assertEqual(self.client.get('/api/admin/help').status_code,403)
        self.assertEqual(self.client.post('/api/admin/mode',json={'enabled':True,'is_admin':True}).status_code,403)

    def test_disconnect_revokes_account_access_and_clears_both_browser_cookies(self):
        self.register(self.client,'reader')
        original=self.client.cookies.get('zenith_login')
        self.client.delete('/api/access').raise_for_status()
        self.assertNotIn(COOKIE,self.client.cookies);self.assertNotIn('zenith_login',self.client.cookies)
        self.assertIsNone(self.agent.personal.user_for_token(original))
        self.assertEqual(self.client.get('/api/account').status_code,401)

    def test_owner_reference_is_locked_for_others_and_no_longer_in_public_quickstart(self):
        self.register(self.client,'reader')
        owner=TestClient(self.app,base_url='https://127.0.0.1');self.register(owner,'owner')
        path=self.agent.admin.initialize('owner',path=self.folder/'private-owner-code.txt')
        self.assertEqual(owner.get('/api/admin/help').status_code,403)
        owner.post('/api/admin/unlock',json={'code':path.read_text().strip()}).raise_for_status()
        reference=owner.get('/api/admin/help');self.assertEqual(reference.status_code,200)
        self.assertIn('commands',reference.json());self.assertNotIn(path.read_text().strip(),reference.text)
        self.assertEqual(self.client.get('/api/admin/help').status_code,403)
        owner.post('/api/admin/lock').raise_for_status()
        self.assertEqual(owner.get('/api/admin/help').status_code,403)
        self.assertNotIn('zenith admin',Path('README.md').read_text(encoding='utf-8'))
        self.assertNotIn('zenith admin',self.client.get('/').text)
        self.assertEqual(self.client.get('/openapi.json').status_code,404)

    def test_unexpected_exception_logs_and_handled_errors_do_not_echo_keys(self):
        @self.app.get('/_test_logs')
        def failure():raise RuntimeError(self.key)
        with self.assertLogs('zenith',level='ERROR') as logs:
            response=self.client.get('/_test_logs')
        self.assertEqual(response.status_code,500)
        self.assertNotIn(self.key,' '.join(logs.output));self.assertNotIn(self.key,response.text)
        self.connect();self.provider.generate.side_effect=ValueError('provider failed '+self.key)
        response=self.client.post('/api/chat',json={'session_id':str(uuid4()),'message':'Explain a tree.'})
        self.assertEqual(response.status_code,400);self.assertNotIn(self.key,response.text)

    def test_keys_are_blocked_from_prompts_memory_feedback_and_public_static_paths(self):
        self.register(self.client,'reader')
        response=self.client.post('/api/chat',json={'session_id':str(uuid4()),'message':'Please store '+self.key})
        self.assertEqual(response.status_code,400);self.provider.generate.assert_not_called()
        self.assertEqual(self.client.post('/api/memories',json={'content':self.key}).status_code,400)
        disguised=self.key[:10]+'\u200b'+self.key[10:]
        self.assertEqual(self.client.post('/api/memories',json={'content':disguised}).status_code,400)
        for path in ('/.env','/data/zenith.sqlite3','/static/../data/zenith.sqlite3','/static/%2e%2e/%2e%2e/config.env'):
            self.assertEqual(self.client.get(path).status_code,404)
        with self.agent.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM turns').fetchone()[0],0)

    def test_cross_account_and_sql_payloads_cannot_read_private_history_or_become_owner(self):
        self.register(self.client,'reader')
        session=str(uuid4());self.client.post('/api/chat',json={'session_id':session,'message':'Explain a tree.'}).raise_for_status()
        other=TestClient(self.app,base_url='https://127.0.0.1');self.register(other,'other')
        self.assertEqual(other.get('/api/history/'+session).status_code,404)
        self.assertEqual(other.post('/api/account/login',json={'username':"reader' OR 1=1 --",'password':'temporary isolated test password'}).status_code,401)
        self.assertEqual(other.get('/api/admin/tools').status_code,403)


class SecretStreamTests(unittest.TestCase):
    def test_discovery_rejects_known_keys_before_external_requests(self):
        from agent.discovery import Discovery
        key=secrets.token_urlsafe(32)
        service=Discovery(redactor=Redactor([key]))
        with patch('agent.discovery.requests.get') as get:
            for kwargs in ({'q':key},{'cursor':key}):
                with self.assertRaises(ValueError):service.search(**kwargs)
            with self.assertRaises(ValueError):service.add('github','owner/'+key)
            get.assert_not_called()

    def test_instruction_pack_key_rejection_rolls_back_every_row(self):
        from agent.skill_catalog import SkillCatalog
        from test_skill_catalog import example, write_pack
        key=secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.redactor=Redactor([key]);catalog=SkillCatalog(store)
            path=Path(folder)/'pack.jsonl';bad=example(1);bad['instruction']='Inspect '+key
            write_pack(path,[example(),bad])
            with self.assertRaises(ValueError):catalog.install(path,True)
            self.assertEqual(catalog.status()['installed_profiles'],0)

    def test_summary_does_not_forward_legacy_credentials_or_persist_model_keys(self):
        from agent import summaries
        key=secrets.token_urlsafe(32)
        provider=Mock();provider.generate.return_value=('Summary '+key,[])
        with tempfile.TemporaryDirectory() as folder:
            agent=Agent(replace(Settings(),provider='huggingface',data_dir=folder,api_token=key),provider)
            user=agent.personal.register('reader','Reader','temporary isolated test password')
            session=str(uuid4());self.assertTrue(agent.personal.conversation_access(session,user['id'],create=True))
            agent.store.add(session,'Explain a tree.','Tree answer.',[],'fixture')
            with agent.store.connect() as db:db.execute('UPDATE turns SET response=?',(key,))
            result=summaries.summarize(agent,user['id'],session)
            self.assertNotIn(key,json.dumps(provider.generate.call_args.args))
            self.assertEqual(result['summary'],'Summary [REDACTED]')

    def test_all_split_positions_and_tiny_chunks_keep_known_and_pattern_secrets_out(self):
        known='opaque-configured-credential-123456789'
        redactor=Redactor([known])
        texts=['Normal text that should stay unchanged.', 'Prefix '+known+' suffix.',
               'Token sk-'+'A'*40+' tail.', 'Token ghp_'+'B'*36+' tail.',
               'password='+'ABCDEF12'*8+' suffix.', 'Bearer '+'D'*50+' suffix.',
               '-----BEGIN PRIVATE KEY-----\n'+'X'*120+'\n-----END PRIVATE KEY----- done.',
               'client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])']
        for text in texts:
            for step in range(1,min(len(text),24)):
                stream=RedactingStream(redactor)
                output=''.join(stream.feed(text[i:i+step]) for i in range(0,len(text),step))+stream.finish()
                self.assertEqual(output,redactor.text(text))
        stream=RedactingStream(redactor)
        with self.assertRaises(ValueError):stream.feed('sk-'+'x'*17000)

    def test_streamed_model_output_and_saved_trace_redact_before_delivery(self):
        key='opaque-configured-credential-123456789'
        class Provider:
            last_deliberation={'api_key':key}
            last_model_label=key
            def stream(self,messages,cancel):
                for character in 'Safe '+key+' end.':yield character,messages
        with tempfile.TemporaryDirectory() as folder:
            agent=Agent(replace(Settings(),provider='huggingface',data_dir=folder,api_token=key),Provider())
            session=str(uuid4());events=list(agent.stream_answer('Explain a tree.',session))
            text=''.join(event['text'] for event in events if event['type']=='delta')
            self.assertEqual(text,'Safe [REDACTED] end.')
            self.assertNotIn(key,json.dumps(events));self.assertNotIn(key,json.dumps(agent.store.history(session)))


class PrivateFileAndDatabaseTests(unittest.TestCase):
    def test_secure_delete_and_supported_defensive_mode_preserve_normal_fts(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder)
            with store.connect() as db:
                self.assertEqual(db.execute('PRAGMA secure_delete').fetchone()[0],1)
                if hasattr(db,'getconfig') and hasattr(sqlite3,'SQLITE_DBCONFIG_DEFENSIVE'):
                    self.assertTrue(db.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE))
            store.add_document('source','https://example.org/research','Independent research about trees.')
            self.assertEqual(len(store.search_documents('trees')),1)
            store.delete_source('source');self.assertEqual(store.search_documents('trees'),[])

    @unittest.skipUnless(os.name=='posix','POSIX owner/mode and symlink checks')
    def test_existing_mfa_key_is_private_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);key=Fernet.generate_key();path=Path(folder)/'owner-mfa.key'
            path.write_bytes(key);path.chmod(0o644)
            self.assertEqual(local_key(store,create=False),key)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            path.unlink();target=Path(folder)/'other.key';target.write_bytes(key);path.symlink_to(target)
            with self.assertRaises(PermissionError):local_key(store,create=False)

    def test_configuration_replacement_is_atomic_and_new_files_are_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.env';path.write_text('PRESERVE=original\n')
            with patch('agent.setup.os.replace',side_effect=OSError('simulated write failure')):
                with self.assertRaises(OSError):write_configuration(path=path,overwrite=True)
            self.assertEqual(path.read_text(),'PRESERVE=original\n')
            self.assertEqual(list(Path(folder).glob('.zenith-config-*')),[])
            if os.name=='posix':
                old=os.umask(0)
                try:write_configuration(path=path,overwrite=True)
                finally:os.umask(old)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)


if __name__=='__main__':unittest.main()
