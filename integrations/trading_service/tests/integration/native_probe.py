"""Actual native provider and service probe. Graph quality is reported, never assumed."""
import argparse
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def provider_probe(root,origin,key_file):
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(root))
    os.environ['OPENAI_COMPATIBLE_API_KEY']=Path(key_file).read_text().strip()
    os.environ['PYTHON_DOTENV_DISABLED']='1'
    from tradingagents.llm_clients import create_tier_client
    cfg={'llm_provider':'openai_compatible','quick_think_llm':'zenith','deep_think_llm':'zenith',
         'backend_url':origin+'/v1','temperature':0,'max_tokens':16,'llm_max_retries':0}
    result=create_tier_client(cfg,'quick').get_llm().invoke('What is 2 plus 2? Answer with the number only.')
    if result.content.strip()!='4':raise AssertionError('Actual native provider inference failed')
    print(json.dumps({'actual_native_provider':True,'scripted_model':False,'answer':result.content,
                      'usage':result.usage_metadata}),flush=True)


def run(args):
    import httpx
    from agent.config import Settings
    from agent.paths import config_file
    from zenith_inference.identity import capture,verify,sha256
    from zenith_inference.backend import NativeBackend
    from zenith_inference.limits import Limits
    from zenith_inference.server import create_app as inference_app
    from zenith_integrations.shared.authorization import ServiceAuth
    from zenith_integrations.shared.secrets import write_private_new
    helper=Path(__file__).resolve().parents[4]/'integrations/inference_service/tests/integration/native_acceptance.py'
    spec=importlib.util.spec_from_file_location('service_test_helper',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    settings=Settings();profile=config_file();profile_before=sha256(profile) if profile.is_file() else None
    import secrets
    report={'scripted_model':False,'live_orders_enabled':False,'full_native_graph_verified':False,'financial_quality_verified':False}
    with tempfile.TemporaryDirectory(prefix='Zenith native financial probe ') as folder:
        private=Path(folder);key=secrets.token_urlsafe(48);write_private_new(private/'inference.key',key)
        manifest=private/'identity.json';capture(settings,manifest)
        backend=NativeBackend(manifest,Limits(8192,256,120));backend.load()
        auth=ServiceAuth([{'id':'tradingagents','token_file':str(private/'inference.key'),
            'models':['zenith'],'capabilities':['inference.read','inference.generate']}])
        with module.serve(inference_app(backend,auth,queue_size=4)) as origin:
            call=[str(args.native_python),str(Path(__file__).resolve()),'--provider-only','--source-root',str(args.source_root),
                  '--inference-origin',origin,'--key-file',str(private/'inference.key')]
            native=json.loads(subprocess.check_output(call,text=True,timeout=150).strip().splitlines()[-1])
            report['provider']=native
            config={'source_root':str(args.source_root.resolve()),'state_directory':str(private/'native-state'),
                    'inference_origin':origin,'inference_key_file':str(private/'inference.key'),
                    'deadline_seconds':600,'max_output_tokens':256}
            native_state=private/'native-state';native_state.mkdir(mode=0o700)
            write_private_new(native_state/'config.json',json.dumps(config))
            service_key=secrets.token_urlsafe(48)
            write_private_new(native_state/'bridge.key',service_key);write_private_new(native_state/'audit.key',secrets.token_urlsafe(48))
            write_private_new(native_state/'services.json',json.dumps({'services':[{'id':'bridge','token_file':str(native_state/'bridge.key'),
                'capabilities':['jobs.read','jobs.submit','jobs.cancel','grants.manage'],'models':[]}]}))
            import socket
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            service=subprocess.Popen([str(args.native_python),'-m','zenith_trading_service.cli','serve','--directory',str(native_state),'--port',str(port)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                with httpx.Client(base_url='http://127.0.0.1:'+str(port),headers={'Authorization':'Bearer '+service_key},timeout=10) as client:
                    deadline=time.monotonic()+20
                    while True:
                        try:
                            response=client.get('/healthz');response.raise_for_status();break
                        except httpx.HTTPError:
                            if time.monotonic()>deadline or service.poll() is not None:raise AssertionError('Actual native service did not become healthy')
                            time.sleep(0.1)
                    start=time.monotonic()
                    body={'account_id':'probe','tickers':['AAPL'],'dates':['2025-01-17']}
                    response=client.post('/v1/jobs',json=body,headers={'Idempotency-Key':'fixed_native_probe'});response.raise_for_status()
                    identifier=response.json()['id'];deadline=time.monotonic()+630
                    while True:
                        state=client.get('/v1/jobs/'+identifier+'?account_id=probe').json()
                        if state['status'] in {'succeeded','failed','cancelled','interrupted'}:break
                        if time.monotonic()>deadline:raise AssertionError('Native worker deadline failed')
                        time.sleep(0.2)
                    report['graph_job']={'status':state['status'],'error_code':state['error_code'],'seconds':time.monotonic()-start}
                    result=state.get('result')
                    if result:
                        report['graph_report']=result
                        report['full_native_graph_verified']=result.get('all_native_roles_completed') is True and result.get('workflow_status')=='completed'
                    report['orders_route_absent']=client.post('/v1/orders',json={}).status_code==404
                    if not report['orders_route_absent']:raise AssertionError('Unexpected order endpoint')
                    client.post('/v1/control/stop').raise_for_status()
                    report['shutdown_persists']=client.get('/healthz').json()['stopped'] is True
            finally:
                service.terminate()
                try:service.wait(20)
                except subprocess.TimeoutExpired:service.kill();service.wait()
        report['original_model_artifacts_unchanged']=verify(manifest)[1]==backend.identity_hash
        report['production_profile_unchanged']=(sha256(profile) if profile.is_file() else None)==profile_before
        if not report['original_model_artifacts_unchanged'] or not report['production_profile_unchanged']:raise AssertionError('Original Zenith artifacts changed')
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-python',type=Path);parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--provider-only',action='store_true');parser.add_argument('--inference-origin');parser.add_argument('--key-file')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.provider_only:provider_probe(args.source_root,args.inference_origin,args.key_file)
    else:run(args)
