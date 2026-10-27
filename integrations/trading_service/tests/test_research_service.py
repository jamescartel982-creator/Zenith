"""Service lifecycle tests use an explicit test executor; production always uses native workers."""
import asyncio
from dataclasses import asdict
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from zenith_integrations.shared.authorization import ServiceAuth,Principal
from zenith_integrations.shared.ledger import Ledger
from zenith_integrations.shared.secrets import write_private_new
from zenith_trading_service.config import TradingConfig
from zenith_trading_service.contracts import ResearchRequest
from zenith_trading_service.execution import NativeExecutor
from zenith_trading_service.reports import analysis_report
from zenith_trading_service.server import create_app


class ResearchContracts(unittest.TestCase):
    def test_orders_provider_overrides_and_invalid_historical_cells_rejected(self):
        body={'account_id':'alice','tickers':['AAPL'],'dates':['2025-01-17']}
        self.assertEqual(ResearchRequest(**body).operation,'research')
        for changed in ({'operation':'live'},{'provider':'other'},{'tickers':['../../keys']},{'dates':['9999-01-01']},
                        {'operation':'backtest','tickers':['AAPL','GOOG','MSFT'],'dates':['2025-01-16','2025-01-17']}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):ResearchRequest(**{**body,**changed})

    def test_missing_risk_evidence_cannot_become_a_tradeable_report(self):
        partial=analysis_report({'final_trade_decision':'Rating: Buy'},'Buy','AAPL','2025-01-17')
        self.assertEqual(partial['rating'],'REVIEW');self.assertFalse(partial['all_native_roles_completed'])
        self.assertIsNone(partial['confidence']);self.assertFalse(partial['live_orders_enabled'])
        state={key:'Evidence fixture' for key in ('market_report','sentiment_report','news_report','fundamentals_report',
            'investment_plan','trader_investment_plan','final_trade_decision')}
        state['investment_debate_state']={'bull_history':'bull','bear_history':'bear'}
        state['risk_debate_state']={'aggressive_history':'risk1','conservative_history':'risk2','neutral_history':'risk3'}
        report=analysis_report(state,'Hold','AAPL','2025-01-17')
        self.assertEqual(report['rating'],'REVIEW');self.assertEqual(report['native_rating'],'Hold');self.assertTrue(report['all_native_roles_completed'])
        state['fundamentals_report']='<tools>unwanted schema echo</tools>'
        echoed=analysis_report(state,'Buy','AAPL','2025-01-17')
        self.assertEqual(echoed['workflow_status'],'requires_review');self.assertIn('prompt_protocol_echo',echoed['quality_flags'])
        self.assertFalse(report['point_in_time']['all_feed_availability_verified'])

    def test_original_defaults_not_mutated_and_all_native_model_tiers_are_zenith(self):
        cfg=TradingConfig('/immutable/native','/private/new','http://127.0.0.1:8781','/private/key')
        default={'llm_provider':'original','data_vendors':{'native':'original'}}
        before=json.dumps(default,sort_keys=True)
        native=cfg.native_config(Path('/immutable/native'),Path('/private/account'),Path('/private/run'),default)
        self.assertEqual(json.dumps(default,sort_keys=True),before)
        self.assertEqual(native['deep_think_llm'],'zenith');self.assertEqual(native['quick_think_llm'],'zenith')
        self.assertEqual(native['quick_think_provider'],'openai_compatible');self.assertTrue(native['checkpoint_enabled'])
        self.assertEqual(native['backend_url'],'http://127.0.0.1:8781/v1')
        with self.assertRaises(ValueError):TradingConfig('/native','/native/state','http://127.0.0.1:8781','/key')

    def test_authenticated_jobs_account_isolation_and_persistent_shutdown(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);secret='s'*48;write_private_new(root/'service.key',secret)
            auth=ServiceAuth([{'id':'bridge','token_file':str(root/'service.key'),
                'capabilities':['jobs.submit','jobs.read','jobs.cancel','grants.manage'],'models':[]}])
            ledger=Ledger(root/'ledger.sqlite3',b'a'*48)
            class Config:
                def verify_source(self):return Path('/verified-test-fixture')
            class Executor:
                config=Config();count=0
                def ready(self):return self.config.verify_source()
                async def execute(self,identifier,principal,request):
                    self.count+=1
                    return {'model':'zenith','workflow_status':'requires_review','live_orders_enabled':False}
            executor=Executor();app=create_app(executor,auth,ledger)
            headers={'Authorization':'Bearer '+secret,'Idempotency-Key':'stable_key'}
            body={'account_id':'alice','tickers':['AAPL'],'dates':['2025-01-17']}
            with TestClient(app,base_url='http://127.0.0.1') as client:
                self.assertEqual(client.post('/v1/jobs',json=body).status_code,401)
                self.assertEqual(client.post('/v1/jobs',headers={**headers,'Origin':'https://attacker.invalid'},json=body).status_code,403)
                self.assertEqual(client.post('/v1/orders',headers=headers,json={}).status_code,404)
                first=client.post('/v1/jobs',headers=headers,json=body).json()
                duplicate=client.post('/v1/jobs',headers=headers,json=body).json()
                self.assertEqual(first['id'],duplicate['id']);self.assertFalse(duplicate['admitted'])
                self.assertEqual(executor.count,1)
                self.assertEqual(client.get('/v1/jobs/'+first['id']+'?account_id=bob',headers=headers).status_code,404)
                result=client.get('/v1/jobs/'+first['id']+'?account_id=alice',headers=headers).json()
                self.assertEqual(result['result']['workflow_status'],'requires_review')
                self.assertTrue(client.post('/v1/control/stop',headers=headers).json()['stopped'])
                self.assertEqual(client.post('/v1/jobs',headers={**headers,'Idempotency-Key':'other_key'},json=body).status_code,503)
            self.assertTrue(Ledger(root/'ledger.sqlite3',b'a'*48).stopped())


class WorkerOwnership(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_during_spawn_reaps_process_without_forwarding_owner_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=TradingConfig('/immutable/native',folder,'http://127.0.0.1:8781','/private/key')
            executor=NativeExecutor(cfg);executor.ready=lambda:None
            original=asyncio.create_subprocess_exec
            admitted=asyncio.Event();release=asyncio.Event();children=[]
            async def delayed(*args,**kwargs):
                self.assertNotIn('ZENITH_ADMIN_CODE',kwargs['env'])
                self.assertNotIn('OPENAI_API_KEY',kwargs['env'])
                child=await original(sys.executable,'-c','import time;time.sleep(60)',start_new_session=os.name=='posix')
                children.append(child);admitted.set();await release.wait();return child
            request=ResearchRequest(account_id='alice',tickers=['AAPL'],dates=['2025-01-17'])
            principal=Principal('bridge',frozenset({'jobs.submit'}),frozenset())
            with patch('zenith_trading_service.execution.asyncio.create_subprocess_exec',side_effect=delayed),patch.dict(os.environ,{'ZENITH_ADMIN_CODE':'fixture-only','OPENAI_API_KEY':'fixture-only'}):
                task=asyncio.create_task(executor.execute('owned_job',principal,request))
                try:
                    await asyncio.wait_for(admitted.wait(),5)
                    task.cancel();release.set()
                    with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(task,10)
                    self.assertEqual(len(children),1);self.assertIsNotNone(children[0].returncode)
                finally:
                    release.set()
                    for child in children:await executor.terminate(child)

    @unittest.skipUnless(os.name=='posix','OS wall-clock alarm is POSIX-specific')
    async def test_worker_deadline_survives_loss_of_parent_supervision(self):
        process=await asyncio.create_subprocess_exec(sys.executable,'-c',
            'from zenith_trading_service.worker import arm_deadline;import time;arm_deadline(0.1);time.sleep(60)')
        code=await asyncio.wait_for(process.wait(),5)
        import signal
        self.assertEqual(code,-signal.SIGALRM)

    async def test_terminate_only_the_owned_process_and_wait_for_exit(self):
        cfg=TradingConfig('/immutable/native','/private/new','http://127.0.0.1:8781','/private/key')
        executor=NativeExecutor(cfg)
        process=await asyncio.create_subprocess_exec(sys.executable,'-c','import time;time.sleep(60)',start_new_session=os.name=='posix')
        await executor.terminate(process)
        self.assertIsNotNone(process.returncode)


if __name__=='__main__':unittest.main()
