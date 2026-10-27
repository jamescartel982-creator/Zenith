"""Launch four real pinned runtimes in fresh test state, then exercise Zenith's bridge."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time


def run(args):
    import httpx
    from zenith_integrations.config import BridgeConfig
    from zenith_integrations.shared.secrets import write_private_new
    from native_openclaw import profile,bootstrap
    from native_four_system import run as acceptance
    used=set()
    def port():
        while True:
            with socket.socket() as s:s.bind(('127.0.0.1',0));p=s.getsockname()[1]
            if p not in used:used.add(p);return p
    with tempfile.TemporaryDirectory(prefix='zenith-four-native-') as directory:
        root=Path(directory);root.chmod(0o700);processes=[]
        def start(command,cwd,env,name):
            log=(root/(name+'.log')).open('wb')
            p=subprocess.Popen([str(x) for x in command],cwd=cwd,env=env,stdout=log,stderr=log,start_new_session=True);log.close();processes.append((name,p));return p
        def checked(command):subprocess.run([str(x) for x in command],check=True,stdout=subprocess.DEVNULL)
        def wait(origin,path,process,headers=None):
            deadline=time.monotonic()+120
            with httpx.Client(base_url=origin,headers=headers,trust_env=False,timeout=3) as client:
                while True:
                    try:
                        response=client.get(path)
                        if response.status_code==200:return
                    except httpx.HTTPError:pass
                    if process.poll() is not None or time.monotonic()>deadline:raise AssertionError('Native service did not become ready')
                    time.sleep(.2)
        try:
            model_port,h_port,o_port,t_port=port(),port(),port(),port()
            model='http://127.0.0.1:'+str(model_port);hermes='http://127.0.0.1:'+str(h_port);trading='http://127.0.0.1:'+str(t_port)
            state=root/'inference';checked([sys.executable,'-m','zenith_inference.cli','init','--directory',state])
            model_process=start([sys.executable,'-m','zenith_inference.cli','serve','--directory',state,'--port',model_port,'--queue-size',4,'--context-tokens',8192,'--max-output-tokens',256],Path.cwd(),os.environ.copy(),'inference')
            operator=(state/'operator.key').read_text().strip();wait(model,'/readyz',model_process,{'Authorization':'Bearer '+operator})
            h_home=root/'hermes-home';h_home.mkdir(mode=0o700);h_key=secrets.token_urlsafe(48);write_private_new(h_home/'api.key',h_key)
            write_private_new(h_home/'.env','API_SERVER_ENABLED=true\nAPI_SERVER_HOST=127.0.0.1\nAPI_SERVER_PORT='+str(h_port)+'\nAPI_SERVER_KEY='+h_key+'\nZENITH_INFERENCE_HERMES_KEY='+(state/'hermes.key').read_text().strip()+'\n')
            config={'_config_version':12,'model':{'default':'zenith','provider':'custom','base_url':model+'/v1','key_env':'ZENITH_INFERENCE_HERMES_KEY','context_length':8192,'max_tokens':256},'platform_toolsets':{'api_server':[]},'agent':{'max_turns':3,'reasoning_effort':False},'gateway':{'api_server':{'enabled':True,'host':'127.0.0.1','port':h_port,'model_name':'hermes-agent','max_concurrent_runs':1}},'fallback_model':None,'auxiliary':{'title_generation':{'enabled':False}}}
            write_private_new(h_home/'config.yaml',json.dumps(config))
            h_env=os.environ.copy();h_env.pop('PYTHONPATH',None);h_env.pop('VIRTUAL_ENV',None);h_env.pop('UV_PROJECT_ENVIRONMENT',None)
            h_env.update(HERMES_HOME=str(h_home),ZENITH_HERMES_CHAT_ONLY='1',ZENITH_HERMES_PROFILE_ID='zenith-hermes-chat',PYTHONDONTWRITEBYTECODE='1')
            h_process=start([args.hermes_python,'-m','gateway.run'],args.hermes_root,h_env,'hermes')
            wait(hermes,'/v1/capabilities',h_process,{'Authorization':'Bearer '+h_key})
            o_home=root/'openclaw-home';o_home.mkdir(mode=0o700);o_owner=secrets.token_urlsafe(48)
            write_private_new(o_home/'openclaw.json',json.dumps(profile(o_home,o_port,model)))
            o_env=os.environ.copy();o_env.update(OPENCLAW_STATE_DIR=str(o_home),OPENCLAW_CONFIG_PATH=str(o_home/'openclaw.json'),ZENITH_TEST_GATEWAY_TOKEN=o_owner,ZENITH_TEST_MODEL_KEY=(state/'openclaw.key').read_text().strip())
            o_process=start([args.node,'openclaw.mjs','gateway','run'],args.openclaw_root,o_env,'openclaw')
            asyncio.run(bootstrap('ws://127.0.0.1:'+str(o_port),o_home,o_owner,o_process))
            t_home=root/'trading-home'
            checked([args.trading_python,'-m','zenith_trading_service.cli','init','--directory',t_home,'--source-root',args.trading_source,'--inference-origin',model,'--inference-key-file',state/'tradingagents.key'])
            t_process=start([args.trading_python,'-m','zenith_trading_service.cli','serve','--directory',t_home,'--port',t_port],Path.cwd(),os.environ.copy(),'tradingagents')
            wait(trading,'/healthz',t_process,{'Authorization':'Bearer '+(t_home/'bridge.key').read_text().strip()})
            # These credentials are service handles, not owner grants or prompts.
            cfg=BridgeConfig('http://127.0.0.1:7860',model,str(state/'operator.key'),str(root/'unused.sqlite3'),audit_key_file=str(root/'unused.key'),job_timeout=600,
              trading_origin=trading,trading_key_file=str(t_home/'bridge.key'),hermes_origin=hermes,hermes_key_file=str(h_home/'api.key'),hermes_profile_id='zenith-hermes-chat',
              openclaw_url='ws://127.0.0.1:'+str(o_port),openclaw_private_key_file=str(o_home/'device.pem'),openclaw_device_token_file=str(o_home/'device.token'),hermes_compat_manifest_file=str(args.hermes_root/'zenith-compat-build.json'))
            write_private_new(root/'bridge.json',json.dumps(asdict(cfg)))
            acceptance(argparse.Namespace(directory=root/'acceptance',identity=state/'identity.json',config=root/'bridge.json',output=args.output))
        finally:
            for name,p in reversed(processes):
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(25)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            # Logs remain private; export only redacted diagnostics on failure.
            if sys.exc_info()[0]:
                from zenith_integrations.shared.redaction import redact
                known=[o_owner] if 'o_owner' in locals() else []
                for keyfile in [p for p in root.rglob('*') if p.suffix in {'.key','.token','.pem'}]:
                    try:known.append(keyfile.read_text().strip())
                    except (OSError,UnicodeError):pass
                diagnostic={'diagnostic_only':True,'all_four_native_workflows_completed':False}
                if args.output.exists():diagnostic=json.loads(args.output.read_text())
                diagnostic['runtime_log_tails']={name:redact((root/(name+'.log')).read_text(errors='replace').splitlines()[-40:],known) for name,p in processes}
                args.output.write_text(json.dumps(diagnostic,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('hermes-root','hermes-python','openclaw-root','node','trading-python','trading-source','output'):parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
