"""Transport, exact grants and cancellation boundaries; fixtures are not native acceptance."""
import asyncio
import json
from pathlib import Path
import tempfile
import time
import unittest
import httpx
from fastapi.testclient import TestClient
from zenith_integrations.config import BridgeConfig
from zenith_integrations.gateway import create_app
from zenith_integrations.shared.ledger import Ledger
from zenith_integrations.shared.router import Router
from zenith_integrations.shared.secrets import write_private_new
from zenith_integrations.tradingagents.client import TradingResearch,PIN
from test_bridge import IdentityFixture,ModelFixture


class NativeTradingClient(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_owner_scope_native_receipt_and_no_payload_credential_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            key=Path(folder)/'native.key';write_private_new(key,'t'*48);posts=[];receipts=[]
            def handle(request):
                self.assertEqual(request.headers['authorization'],'Bearer '+'t'*48)
                if request.url.path=='/healthz':return httpx.Response(200,json={'runtime':'tradingagents','model':'zenith','target_source_pin':PIN,'stopped':False,'live_orders_enabled':False})
                if request.method=='POST':
                    posts.append(json.loads(request.content));self.assertEqual(request.headers['idempotency-key'],'bridge_job')
                    return httpx.Response(202,json={'id':'native_job','status':'queued'})
                self.assertEqual(request.headers['x-zenith-account'],'owner_id')
                return httpx.Response(200,json={'id':'native_job','status':'succeeded','result':{'model':'zenith','live_orders_enabled':False,'rating':'REVIEW'}})
            client=TradingResearch('http://127.0.0.1:8783',key,transport=httpx.MockTransport(handle))
            report=await client.execute_scoped({'ticker':'AAPL','as_of':'2025-01-17'},'owner_id','bridge_job','research',lambda *value:receipts.append(value))
            self.assertEqual(len(posts),1);self.assertEqual(posts[0]['account_id'],'owner_id')
            self.assertEqual(receipts[0],('native_job',));self.assertEqual(report['native_job_id'],'native_job')
            with self.assertRaises(RuntimeError):await client.execute_scoped({'ticker':'AAPL','as_of':'2025-01-17','account_id':'other'},'owner_id','bridge_job','research',lambda *value:None)
            self.assertEqual(len(posts),1)


class ScopedGateway(unittest.TestCase):
    def test_revoked_owner_lease_cancels_native_work_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ledger=Ledger(root/'ledger.sqlite3',b'a'*48);router=Router(ModelFixture())
            class Research:
                cancelled=False
                async def execute_scoped(self,payload,account_id,job_id,operation,on_admitted):
                    self.account=account_id;on_admitted('owned_native_job')
                    try:await asyncio.sleep(30)
                    except asyncio.CancelledError:
                        self.cancelled=True;on_admitted('owned_native_job','cancelled');raise
            native=Research();router.adapters['tradingagents']=native
            cfg=BridgeConfig('http://127.0.0.1:7860','http://127.0.0.1:8781','unused',str(ledger.path),job_timeout=10)
            app=create_app(cfg,identity=IdentityFixture(),router=router,ledger=ledger)
            with TestClient(app,base_url='http://127.0.0.1') as api:
                api.cookies.set('zenith_login','owner-session-token')
                scope={'runtime':'tradingagents','operation':'research','ticker':'AAPL','as_of':'2025-01-17'}
                grant=api.post('/v1/grants',json={'capability':'jobs.submit.tradingagents','scope':scope,'seconds':10}).json()
                body={'runtime':'tradingagents','operation':'research','grant_id':grant['id'],'payload':{'ticker':'MSFT','as_of':'2025-01-17'}}
                self.assertEqual(api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'wrong_scope'}).status_code,403)
                body['payload']['ticker']='AAPL'
                admitted=api.post('/v1/jobs',json=body,headers={'Idempotency-Key':'right_scope'}).json()
                time.sleep(0.05)
                self.assertEqual(native.account,'owner')
                api.delete('/v1/grants/'+grant['id'])
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    state=api.get('/v1/jobs/'+admitted['id']).json()
                    if state['status']=='failed':break
                    time.sleep(0.05)
                self.assertTrue(native.cancelled)
                self.assertEqual(state['native_receipt']['native_status'],'cancelled')
                self.assertEqual(state['native_receipt']['native_job_id'],'owned_native_job')
                self.assertEqual(state['status'],'failed')
