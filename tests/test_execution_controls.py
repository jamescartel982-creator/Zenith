"""Owner MFA, scope validation, revocation and retained legacy accounts."""
import hashlib
import json
from pathlib import Path
import secrets
import socket
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
import pyotp
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.personal import PersonalStore
from agent.execution import authorized_addresses,scope_definition


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.now=time.time()
        clock=patch('agent.owner_mfa.time.time',side_effect=lambda:self.now);clock.start();self.addCleanup(clock.stop)
        self.agent=Agent(Settings(provider='ollama',data_dir=self.folder.name),provider=Mock())
        self.owner=TestClient(create_app(agent=self.agent,settings=self.agent.settings))
        self.password='owner test account password'
        self.user=self.owner.post('/api/account/register',json={'username':'owner','display_name':'Owner','password':self.password}).json()['user']
        code_path=Path(self.folder.name)/'owner-fixture.txt'
        self.agent.admin.initialize('owner',code_path);self.code=code_path.read_text().strip()
        self.token=self.owner.cookies.get('zenith_login')
        self.assertEqual(self.owner.post('/api/admin/unlock',json={'code':self.code}).status_code,200)

    def enroll(self):
        result=self.owner.post('/api/admin/mfa/setup',json={'password':self.password})
        self.assertEqual(result.status_code,200,result.text)
        secret=result.json()['secret']
        self.assertEqual(self.owner.post('/api/admin/mfa/confirm',json={'otp':pyotp.TOTP(secret).at(self.now)}).status_code,200)
        return secret

    def test_passwords_are_argon2id_and_legacy_hashes_migrate_on_valid_login(self):
        with self.agent.store.connect() as db:
            self.assertTrue(db.execute('SELECT password_hash FROM users').fetchone()[0].startswith('$argon2id$'))
            salt=secrets.token_hex(16);legacy=PersonalStore.password_hash(self.password,salt)
            db.execute('UPDATE users SET salt=?,password_hash=?',(salt,legacy))
        self.assertIsNone(self.agent.personal.login('owner','incorrect password'))
        with self.agent.store.connect() as db:self.assertEqual(db.execute('SELECT password_hash FROM users').fetchone()[0],legacy)
        self.assertIsNotNone(self.agent.personal.login('owner',self.password))
        with self.agent.store.connect() as db:self.assertTrue(db.execute('SELECT password_hash FROM users').fetchone()[0].startswith('$argon2id$'))

    def test_restricted_capabilities_are_disabled_until_mfa_and_explicit_grant(self):
        request={'capability':'code-audit','arguments':{'text':'print(1)'}}
        self.assertEqual(self.owner.post('/api/admin/execution/run',json=request).status_code,403)
        self.assertEqual(self.owner.post('/api/admin/execution/grant',json={'capability':'code-audit','scope':{'kind':'offline'}}).status_code,403)
        secret=self.enroll()
        self.assertEqual(self.owner.post('/api/admin/execution/run',json=request).status_code,403)
        result=self.owner.post('/api/admin/execution/grant',json={'capability':'code-audit','scope':{'kind':'offline'}})
        self.assertEqual(result.status_code,200,result.text)
        result=self.owner.post('/api/admin/execution/run',json=request)
        self.assertEqual(result.status_code,200,result.text)
        self.assertNotIn(secret,result.text)
        with self.agent.store.connect() as db:
            row=db.execute('SELECT secret FROM owner_mfa').fetchone()
            self.assertNotEqual(row['secret'],secret)
        self.assertEqual(self.owner.post('/api/admin/mfa/setup',json={'password':self.password}).status_code,400)

    def test_mfa_replay_logout_and_code_only_unlock_are_rejected(self):
        secret=self.enroll();used=pyotp.TOTP(secret).at(self.now)
        self.assertFalse(self.agent.admin.mfa.verify(self.user['id'],self.token,used))
        self.owner.post('/api/admin/lock')
        self.assertEqual(self.owner.post('/api/admin/unlock',json={'code':self.code}).status_code,403)
        self.assertEqual(self.owner.post('/api/admin/unlock',json={'code':self.code,'otp':used}).status_code,403)
        self.now+=31
        result=self.owner.post('/api/admin/unlock',json={'code':self.code,'otp':pyotp.TOTP(secret).at(self.now)})
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()['mfa_verified'])
        self.owner.post('/api/account/logout')
        self.assertFalse(self.agent.admin.mfa.verified(self.user['id'],self.token))

    def test_authenticator_seed_never_enters_chat_or_saved_memory(self):
        secret=self.enroll()
        from uuid import uuid4
        result=self.owner.post('/api/chat',json={'session_id':str(uuid4()),'message':'Remember '+secret})
        self.assertEqual(result.status_code,400)
        self.assertEqual(self.owner.post('/api/memories',json={'content':secret}).status_code,400)
        self.agent.provider.generate.assert_not_called()

    def test_network_target_scope_is_checked_before_any_connection(self):
        self.enroll()
        with socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(4);port=server.getsockname()[1]
            scope={'kind':'network','cidrs':['127.0.0.1/32'],'ports':[port],'authorization_reference':'Owned loopback test fixture'}
            result=self.owner.post('/api/admin/execution/grant',json={'capability':'tcp-connect','scope':scope})
            self.assertEqual(result.status_code,200,result.text)
            result=self.owner.post('/api/admin/execution/run',json={'capability':'tcp-connect','arguments':{'host':'127.0.0.1','port':port}})
            self.assertEqual(result.status_code,200,result.text)
            self.assertTrue(result.json()['result']['reachable'])
            with patch('agent.execution.socket.create_connection') as connection:
                result=self.owner.post('/api/admin/execution/run',json={'capability':'tcp-connect','arguments':{'host':'192.0.2.42','port':port}})
                self.assertEqual(result.status_code,403)
                connection.assert_not_called()
            with patch('agent.execution.socket.create_connection') as connection:
                result=self.owner.post('/api/admin/execution/run',json={'capability':'tcp-connect','arguments':{'host':'127.0.0.1','port':port+1}})
                self.assertEqual(result.status_code,403);connection.assert_not_called()

    def test_emergency_stop_and_expiry_clear_effective_permission(self):
        self.enroll()
        grant={'capability':'inspect-url','scope':{'kind':'offline'}}
        self.assertEqual(self.owner.post('/api/admin/execution/grant',json=grant).status_code,200)
        self.assertEqual(self.owner.post('/api/admin/execution/stop').status_code,200)
        self.assertEqual(self.owner.post('/api/admin/execution/grant',json=grant).status_code,403)
        self.assertEqual(self.owner.post('/api/admin/execution/resume').status_code,200)
        self.assertEqual(self.owner.get('/api/admin/execution').json()['active_grants'],[])
        self.owner.post('/api/admin/execution/grant',json=grant|{'seconds':1})
        self.now+=2
        result=self.owner.post('/api/admin/execution/run',json={'capability':'inspect-url','arguments':{'text':'https://example.org'}})
        self.assertEqual(result.status_code,403)

    def test_old_tool_endpoint_cannot_bypass_new_capability_checks(self):
        self.owner.post('/api/admin/mode',json={'enabled':True})
        data={'tool':'code-audit','text':'print(1)'}
        self.assertEqual(self.owner.post('/api/admin/tools',json=data).status_code,403)
        self.enroll()
        self.assertEqual(self.owner.post('/api/admin/tools',json=data).status_code,403)
        self.owner.post('/api/admin/execution/grant',json={'capability':'code-audit','scope':{'kind':'offline'}})
        self.assertEqual(self.owner.post('/api/admin/tools',json=data).status_code,200)

    def test_plan_records_progress_and_stops_on_permission_failure(self):
        self.enroll()
        self.owner.post('/api/admin/execution/grant',json={'capability':'inspect-url','scope':{'kind':'offline'}})
        steps=[{'tool':'inspect-url','arguments':{'text':'https://example.org'}},{'tool':'code-audit','arguments':{'text':'do not retain this source'}}]
        self.assertEqual(self.owner.post('/api/admin/execution/plan',json={'steps':steps}).status_code,403)
        history=self.owner.get('/api/admin/execution/history').json()
        self.assertEqual(history['tasks'][0]['status'],'failed')
        self.assertEqual(json.loads(history['tasks'][0]['results'])['completed_steps'],1)
        self.assertNotIn('do not retain this source',json.dumps(history))
        self.assertTrue(any(e['event']=='denied' for e in history['events']))

    def test_scope_rejects_broad_networks_ambiguous_arguments_and_mixed_dns(self):
        with self.assertRaises(ValueError):scope_definition({'kind':'network','cidrs':['0.0.0.0/0'],'ports':[443],'authorization_reference':'lab'},True)
        scope={'ports':[443],'cidrs':['192.0.2.0/24']}
        addresses=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.1',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('169.254.169.254',443))]
        with patch('agent.execution.socket.getaddrinfo',return_value=addresses) as resolver:
            with self.assertRaises(ValueError):authorized_addresses('fixture.example',443,scope)
            resolver.assert_not_called()

    def test_regular_account_and_forged_owner_identity_cannot_execute(self):
        self.enroll()
        other=self.agent.personal.register('visitor','Visitor',self.password)
        token=self.agent.personal.issue_session(other['id'])
        with self.assertRaises(PermissionError):self.agent.execution.grant(self.user['id'],token,'code-audit',{'kind':'offline'})
        with self.assertRaises(PermissionError):self.agent.execution.grant(other['id'],token,'code-audit',{'kind':'offline'})
