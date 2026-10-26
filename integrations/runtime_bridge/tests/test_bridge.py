"""Native account isolation, durable job ownership and server-side grants."""
import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from fastapi import HTTPException
from fastapi.testclient import TestClient
from zenith_integrations.config import BridgeConfig
from zenith_integrations.gateway import create_app
from zenith_integrations.shared.identity import User
from zenith_integrations.shared.ledger import Conflict, Ledger
from zenith_integrations.shared.router import Router
from zenith_integrations.shared.secrets import write_private_new


class IdentityFixture:
    async def verify(self, token, owner=False):
        if token not in ('owner-session-token','reader-session-token'):
            raise HTTPException(401,'Sign in')
        if owner and token != 'owner-session-token':
            raise HTTPException(403,'Verified owner MFA required')
        return User('owner' if token.startswith('owner') else 'reader',token)


class ModelFixture:
    def __init__(self):
        self.calls=0
    async def execute(self,payload):
        self.calls+=1
        await asyncio.sleep(0.02)
        return {'model':'zenith','object':'chat.completion','choices':[{'message':{'role':'assistant','content':'4'}}]}
    async def health(self):
        return True


class LedgerTests(unittest.TestCase):
    def test_foreign_native_database_is_never_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'native.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE conversations(secret TEXT)')
            path.chmod(0o600)
            before=path.read_bytes()
            with self.assertRaises(ValueError):
                Ledger(path,b'a'*48)
            self.assertEqual(path.read_bytes(),before)

    def test_idempotence_session_isolation_tampering_and_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'control.sqlite3',b'a'*48)
            user=User('owner','session')
            request={'runtime':'zenith','operation':'chat','payload':{'messages':[]}}
            row,new=ledger.admit(user,'stable-key',request)
            self.assertTrue(new)
            self.assertFalse(ledger.admit(User('owner','new-login'),'stable-key',request)[1])
            with self.assertRaises(Conflict):ledger.admit(user,'stable-key',request|{'operation':'other'})
            self.assertIsNone(ledger.get(row['id'],User('reader','session')))
            self.assertTrue(ledger.transition(row['id'],{'queued'},'running'))
            self.assertEqual(ledger.recover(),1)
            self.assertEqual(ledger.get(row['id'],user)['status'],'interrupted')
            self.assertTrue(ledger.verify_audit())
            with ledger.connect() as db:db.execute("UPDATE audit SET event='forged' WHERE seq=1")
            self.assertFalse(ledger.verify_audit())
            with self.assertRaises(ValueError):Ledger(ledger.path,b'a'*48)

    def test_grants_are_exact_short_lived_and_login_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'control.sqlite3',b'a'*48)
            user=User('owner','session')
            scope={'runtime':'hermes','operation':'support'}
            grant=ledger.grant(user,'jobs.submit.hermes',scope,60)
            self.assertTrue(ledger.allows(user,grant['id'],'jobs.submit.hermes',scope))
            self.assertFalse(ledger.allows(User('owner','new-login'),grant['id'],'jobs.submit.hermes',scope))
            self.assertFalse(ledger.allows(user,grant['id'],'jobs.submit.hermes',scope|{'operation':'chat'}))
            ledger.shutdown(user)
            self.assertTrue(Ledger(ledger.path,b'a'*48).stopped())
            ledger.resume(user)
            self.assertFalse(ledger.stopped())
            self.assertFalse(ledger.allows(user,grant['id'],'jobs.submit.hermes',scope))


class GatewayTests(unittest.TestCase):
    def test_job_ownership_real_lifecycle_and_no_native_placeholder_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            config=BridgeConfig('http://127.0.0.1:7860','http://127.0.0.1:8781',str(folder/'model.key'),str(folder/'control.sqlite3'))
            ledger=Ledger(config.database,b'a'*48)
            model=ModelFixture()
            app=create_app(config,identity=IdentityFixture(),router=Router(model),ledger=ledger)
            body={'runtime':'zenith','operation':'chat','payload':{'model':'zenith','messages':[{'role':'user','content':'2+2'}]}}
            with TestClient(app,base_url='http://127.0.0.1') as api:
                self.assertEqual(api.post('/v1/jobs',json=body).status_code,401)
                api.cookies.set('zenith_login','owner-session-token')
                first=api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'stable-key'})
                self.assertEqual(first.status_code,202,first.text)
                identifier=first.json()['id']
                second=api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'stable-key'})
                self.assertEqual(second.json()['id'],identifier)
                for _ in range(50):
                    result=api.get('/v1/jobs/'+identifier)
                    if result.json()['status']=='succeeded':break
                    time.sleep(0.01)
                self.assertEqual(result.json()['status'],'succeeded',result.text)
                self.assertEqual(model.calls,1)
                self.assertEqual(api.get('/v1/jobs/'+identifier+'/result').json()['result']['model'],'zenith')
                self.assertEqual(api.post('/v1/jobs',json=body|{'runtime':'hermes','operation':'support'},headers={'Idempotency-Key':'hermes-key'}).status_code,503)
                api.cookies.set('zenith_login','reader-session-token')
                self.assertEqual(api.get('/v1/jobs/'+identifier).status_code,404)
                self.assertEqual(api.get('/v1/jobs/'+identifier+'/result').status_code,404)
                self.assertEqual(api.post('/v1/grants',json={'capability':'jobs.submit.hermes','scope':{'runtime':'hermes','operation':'support'}}).status_code,403)
                api.cookies.set('zenith_login','owner-session-token')
                self.assertEqual(api.post('/v1/control/stop').status_code,200)
                self.assertEqual(api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'new-stable-key'}).status_code,503)
                self.assertEqual(api.post('/v1/control/resume').status_code,200)

class NativeIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_zenith_login_mfa_logout_and_prompt_role_spoofing(self):
        import httpx
        import pyotp
        from unittest.mock import Mock
        from agent.config import Settings
        from agent.core import Agent
        from agent.server import create_app as native_app
        from zenith_integrations.shared.identity import ZenithIdentity
        with tempfile.TemporaryDirectory() as folder:
            settings=Settings(provider='huggingface',data_dir=folder)
            agent=Agent(settings,provider=Mock())
            transport=httpx.ASGITransport(app=native_app(settings,agent=agent))
            config=BridgeConfig('http://127.0.0.1:7860','http://127.0.0.1:8781',str(Path(folder)/'unused.key'),str(Path(folder)/'unused.sqlite3'))
            verifier=ZenithIdentity(config,transport=transport)
            async with httpx.AsyncClient(transport=transport,base_url=config.zenith_origin) as api:
                password='isolated owner test password'
                response=await api.post('/api/account/register',json={'username':'owner','display_name':'Owner','password':password})
                self.assertEqual(response.status_code,200,response.text)
                token=api.cookies['zenith_login']
                owner=(await verifier.verify(token)).id
                code_path=Path(folder)/'test-owner.txt'
                agent.admin.initialize('owner',code_path)
                response=await api.post('/api/admin/unlock',json={'code':code_path.read_text().strip()})
                self.assertEqual(response.status_code,200,response.text)
                # Original code-only owner elevation must NOT grant bridge control.
                with self.assertRaises(HTTPException) as denied:await verifier.verify(token,owner=True)
                self.assertEqual(denied.exception.status_code,403)
                setup=await api.post('/api/admin/mfa/setup',json={'password':password})
                secret=setup.json()['secret']
                confirmed=await api.post('/api/admin/mfa/confirm',json={'otp':pyotp.TOTP(secret).now()})
                self.assertEqual(confirmed.status_code,200,confirmed.text)
                self.assertEqual((await verifier.verify(token,owner=True)).id,owner)
                await api.post('/api/account/logout')
                with self.assertRaises(HTTPException):await verifier.verify(token,owner=True)
            agent.provider.generate.assert_not_called()
