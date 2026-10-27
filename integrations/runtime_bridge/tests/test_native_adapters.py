"""Execution ownership and permission regressions; native acceptance is separate."""
import asyncio
import tempfile
import time
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from zenith_integrations.config import BridgeConfig
from zenith_integrations.gateway import create_app
from zenith_integrations.hermes.adapter import HermesChat
from zenith_integrations.hermes.api_client import HermesRun
from zenith_integrations.openclaw.adapter import OpenClawChat
from zenith_integrations.shared.ledger import Ledger
from zenith_integrations.shared.native_task import chat_scope
from zenith_integrations.shared.native_http import UnknownExecution
from zenith_integrations.shared.router import Router
from test_bridge import IdentityFixture, ModelFixture


class NativeAdapters(unittest.IsolatedAsyncioTestCase):
    async def test_hermes_account_binding_completion_and_no_overrides(self):
        class API:
            def __init__(self): self.http=self; self.calls=[]
            async def discover(self): return {}
            async def request(self,*args): return {'object':'list','platform':'api_server','data':[{'enabled':False}]}
            async def submit(self,text,session,key):
                self.calls.append((text,session,key));return HermesRun('native_run',session,key,'profile')
            async def wait(self,handle,seconds): return {'status':'completed','runtime':{'model':'zenith','provider':'custom'}}
        api=API();adapter=HermesChat(api,'profile',b's'*32);receipts=[]
        payload={'message':'2+2','conversation_id':'one'}
        result=await adapter.execute_scoped(payload,'owner','bridgejob','chat',lambda *a:receipts.append(a))
        await adapter.execute_scoped(payload,'other','bridgejob2','chat',lambda *a:None)
        self.assertNotEqual(api.calls[0][1],api.calls[1][1]);self.assertEqual(result['native_job_id'],'native_run')
        self.assertEqual(receipts[-1],('native_run','completed'))
        with self.assertRaises(RuntimeError): await adapter.execute_scoped(payload|{'provider':'external'},'owner','job','chat',lambda *a:None)
        self.assertEqual(len(api.calls),2)
        async def enabled(*args):return {'object':'list','platform':'api_server','data':[{'enabled':True}]}
        api.request=enabled;self.assertFalse(await adapter.health())

    async def test_cancel_hermes_confirms_native_stop_or_reports_unknown(self):
        class API:
            def __init__(self): self.http=self;self.stopped=False
            async def discover(self):return {}
            async def request(self,*args):return {'object':'list','platform':'api_server','data':[]}
            async def submit(self,text,session,key):return HermesRun('run',session,key,'profile')
            async def stop(self,handle):self.stopped=True
            async def wait(self,handle,seconds):
                if self.stopped:return {'status':'interrupted'}
                await asyncio.sleep(30)
        api=API();adapter=HermesChat(api,'profile',b's'*32);event=asyncio.Event()
        task=asyncio.create_task(adapter.execute_scoped({'message':'hello','conversation_id':'one'},'owner','job','chat',lambda *a:event.set()))
        await event.wait();task.cancel()
        with self.assertRaises(UnknownExecution):await task
        self.assertTrue(api.stopped)

    async def test_openclaw_only_returns_matched_terminal_and_isolates_sessions(self):
        calls=[]
        class Client:
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            async def health(self):return {'ok':True}
            async def submit_turn(self,session,message,key):calls.append((session,message,key));return {'runId':'native_run'}
            async def terminal(self,session,run,seconds):return {'state':'final','message':{'content':'4'},'local_model_may_still_be_finishing':False}
        adapter=OpenClawChat(Client,'profile',b's'*32);self.assertTrue(await adapter.health())
        payload={'message':'2+2','conversation_id':'one'}
        result=await adapter.execute_scoped(payload,'owner','bridge_job','chat',lambda *a:None)
        await adapter.execute_scoped(payload,'other','bridge_job2','chat',lambda *a:None)
        self.assertNotEqual(calls[0][0],calls[1][0]);self.assertEqual(result['result']['state'],'final')
        with self.assertRaises(RuntimeError):await adapter.execute_scoped(payload|{'session_key':'foreign'},'owner','job','chat',lambda *a:None)


class RuntimePermissions(unittest.TestCase):
    def test_exact_message_grants_owner_only_and_revocation_cancel_both_runtimes(self):
        for runtime in ('hermes','openclaw'):
            with self.subTest(runtime=runtime),tempfile.TemporaryDirectory() as folder:
                ledger=Ledger(Path(folder)/'control.sqlite3',b'a'*48);router=Router(ModelFixture())
                class Native:
                    cancelled=False
                    async def execute_scoped(self,payload,account,job,operation,on_admitted):
                        self.account=account;on_admitted('native_run')
                        try:await asyncio.sleep(30)
                        except asyncio.CancelledError:self.cancelled=True;on_admitted('native_run','cancelled');raise
                native=Native();router.adapters[runtime]=native
                cfg=BridgeConfig('http://127.0.0.1:7860','http://127.0.0.1:8781','unused',str(ledger.path),job_timeout=10)
                with TestClient(create_app(cfg,identity=IdentityFixture(),router=router,ledger=ledger),base_url='http://127.0.0.1') as api:
                    payload={'message':'hello','conversation_id':'one'}
                    scope={'runtime':runtime,'operation':'chat',**chat_scope(payload,'chat')}
                    api.cookies.set('zenith_login','reader-session-token')
                    self.assertEqual(api.post('/v1/grants',json={'capability':'jobs.submit.'+runtime,'scope':scope}).status_code,403)
                    api.cookies.set('zenith_login','owner-session-token')
                    grant=api.post('/v1/grants',json={'capability':'jobs.submit.'+runtime,'scope':scope,'seconds':10}).json()
                    body={'runtime':runtime,'operation':'chat','payload':payload|{'message':'different'},'grant_id':grant['id']}
                    self.assertEqual(api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'wrong_scope'}).status_code,403)
                    body['payload']=payload
                    row=api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'right_scope'}).json()
                    time.sleep(.05);api.delete('/v1/grants/'+grant['id'])
                    deadline=time.monotonic()+4
                    while time.monotonic()<deadline:
                        state=api.get('/v1/jobs/'+row['id']).json()
                        if state['status']=='failed':break
                        time.sleep(.05)
                    self.assertTrue(native.cancelled);self.assertEqual(native.account,'owner')
                    self.assertEqual(state['native_receipt']['native_status'],'cancelled')

    def test_partial_or_remote_configuration_is_refused(self):
        base=dict(zenith_origin='http://127.0.0.1:7860',inference_origin='http://127.0.0.1:8781',inference_key_file='a',database='b')
        for values in ({'hermes_origin':'http://127.0.0.1:8642'}, {'openclaw_url':'ws://127.0.0.1:18789'}, {'hermes_origin':'https://external.test','hermes_key_file':'key','audit_key_file':'audit'}):
            with self.assertRaises(ValueError):BridgeConfig(**base,**values)
