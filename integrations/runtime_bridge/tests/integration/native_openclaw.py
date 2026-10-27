"""Real pinned OpenClaw -> verified Zenith -> original owner/MFA bridge acceptance."""
import argparse
import asyncio
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import uuid


def check(value, message):
    if not value:raise AssertionError(message)


def profile(root, port, inference):
    return {'gateway':{'mode':'local','port':port,'bind':'loopback','auth':{'mode':'token','token':{'source':'env','provider':'default','id':'ZENITH_TEST_GATEWAY_TOKEN'}},'controlUi':{'enabled':False},'terminal':{'enabled':False},'nodes':{'pairing':{'sshVerify':False}},'tailscale':{'mode':'off'}},
      'models':{'mode':'replace','providers':{'zenith':{'baseUrl':inference+'/v1','api':'openai-completions','apiKey':{'source':'env','provider':'default','id':'ZENITH_TEST_MODEL_KEY'},'models':[{'id':'zenith','name':'Zenith','reasoning':False,'input':['text'],'contextWindow':8192,'maxTokens':256,'cost':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0},'compat':{'supportsDeveloperRole':False,'supportsStore':False,'supportsTools':False,'supportsReasoningEffort':False,'maxTokensField':'max_tokens','requiresStringContent':True}}]}}},
      'agents':{'ownership':'explicit','defaults':{'workspace':str(root/'workspace'),'model':{'primary':'zenith/zenith','fallbacks':[]},'thinkingDefault':'off','maxConcurrent':1,'systemAgent':{'agentId':'zenith'},'skipBootstrap':True},'entries':{'zenith':{'name':'Zenith','workspace':str(root/'workspace'),'model':{'primary':'zenith/zenith','fallbacks':[]},'tools':{'deny':['*']}}}},
      'tools':{'deny':['*']},'browser':{'enabled':False},'cron':{'enabled':False},'plugins':{'enabled':False},
      'commands':{'native':False,'nativeSkills':False,'text':False,'bash':False,'config':False,'mcp':False,'plugins':False,'debug':False,'restart':False}}


async def bootstrap(url, root, owner, process):
    from cryptography.hazmat.primitives import serialization
    from websockets.asyncio.client import connect
    from zenith_integrations.openclaw.gateway_client import create_device, device_payload, b64url, GatewayClient
    from zenith_integrations.shared.secrets import read_private, write_private_new
    create_device(root/'device.pem')
    private=serialization.load_pem_private_key(read_private(root/'device.pem').encode(),password=None)
    public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    device_id=hashlib.sha256(public).hexdigest();scopes=['operator.read','operator.write']
    deadline=time.monotonic()+90
    while True:
        try:ws=await connect(url,proxy=None,open_timeout=3,max_size=1024*1024);break
        except (OSError,TimeoutError):
            check(process.poll() is None and time.monotonic()<deadline,'Native Gateway startup did not finish')
            await asyncio.sleep(.25)
    async with ws:
        challenge=json.loads(await asyncio.wait_for(ws.recv(),30))['payload'];ts,nonce=challenge['ts'],challenge['nonce']
        # Explicit owner setup in fresh test state. Backend self-connections do
        # not create native device grants; the documented protocol CLI mode does.
        signed=device_payload(device_id,'gateway-client','cli','operator',scopes,ts,owner,nonce,'python')
        request_id=uuid.uuid4().hex
        params={'minProtocol':4,'maxProtocol':4,'client':{'id':'gateway-client','version':'0.3.0','platform':'python','mode':'cli'},'role':'operator','scopes':scopes,'caps':[],'auth':{'token':owner},'device':{'id':device_id,'publicKey':b64url(public),'signature':b64url(private.sign(signed.encode())),'signedAt':ts,'nonce':nonce}}
        await ws.send(json.dumps({'type':'req','id':request_id,'method':'connect','params':params}))
        while True:
            response=json.loads(await asyncio.wait_for(ws.recv(),30))
            if response.get('type')=='res' and response.get('id')==request_id:break
        check(response.get('ok') is True,'Native owner device setup was refused')
        auth=response['payload']['auth']
        check(set(auth['scopes'])==set(scopes) and bool(auth.get('deviceToken')),'Native least-privilege device grant was not issued')
        write_private_new(root/'device.token',auth['deviceToken'])
    async with GatewayClient(url,root/'device.pem',root/'device.token') as client:
        check(client.hello['auth'].get('method')=='device-token','Shared owner credentials leaked into the bridge connection')
        value=await client.health();check(value.get('ok') is True,'Actual paired native health failed')
        return {'paired':True,'scopes':client.hello['auth']['scopes'],'server_version':client.hello['server']['version'],'build_id':client.hello['server'].get('buildId')}


def run(args):
    import httpx
    import pyotp
    from agent.config import Settings
    from agent.core import Agent
    from agent.server import create_app as accounts_app
    from zenith_inference.backend import NativeBackend
    from zenith_inference.identity import capture,verify
    from zenith_inference.limits import Limits
    from zenith_inference.server import create_app as inference_app
    from zenith_integrations.config import BridgeConfig
    from zenith_integrations.gateway import create_app as bridge_app
    from zenith_integrations.openclaw.gateway_client import PIN
    from zenith_integrations.shared.authorization import ServiceAuth
    from zenith_integrations.shared.native_task import chat_scope
    from zenith_integrations.shared.secrets import write_private_new
    helper=Path(__file__).resolve().parents[4]/'integrations/inference_service/tests/integration/native_acceptance.py'
    spec=importlib.util.spec_from_file_location('tcp_acceptance',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=Path(args.native_root).resolve()
    check(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==PIN,'OpenClaw source pin mismatch')
    check(subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD']).returncode==0,'Tracked native source was changed')
    report={'source_pin':PIN,'scripted_model':False,'native_tools_enabled':False,'external_message_sent':False,'live_orders_enabled':False}
    with tempfile.TemporaryDirectory(prefix='zenith-native-openclaw-') as directory:
        root=Path(directory);root.chmod(0o700);capture(Settings(),root/'identity.json');metrics=[]
        class MeasuredBackend(NativeBackend):
            def complete(self,*args,**kwargs):
                value=super().complete(*args,**kwargs)
                metrics.append({'prompt_tokens':value.prompt_tokens,'completion_tokens':value.completion_tokens})
                return value
        backend=MeasuredBackend(root/'identity.json',Limits(8192,256,120));backend.load();identity=backend.identity_hash
        key=secrets.token_urlsafe(48);write_private_new(root/'model.key',key)
        auth=ServiceAuth([{'id':'openclaw-test','token_file':str(root/'model.key'),'models':['zenith'],'capabilities':['inference.read','inference.generate']}])
        with module.serve(inference_app(backend,auth,queue_size=4)) as inference:
            home=root/'openclaw';home.mkdir(mode=0o700)
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            owner=secrets.token_urlsafe(48);config=profile(home,port,inference)
            write_private_new(home/'openclaw.json',json.dumps(config))
            env=os.environ.copy();env.update(OPENCLAW_STATE_DIR=str(home),OPENCLAW_CONFIG_PATH=str(home/'openclaw.json'),ZENITH_TEST_GATEWAY_TOKEN=owner,ZENITH_TEST_MODEL_KEY=key)
            logfile=root/'native-gateway.log'
            with logfile.open('wb') as log:
                process=subprocess.Popen([str(args.node),'openclaw.mjs','gateway','run'],cwd=source,env=env,stdout=log,stderr=log)
            try:
                url='ws://127.0.0.1:'+str(port)
                report['native_device']=asyncio.run(bootstrap(url,home,owner,process))
                settings=replace(Settings(),data_dir=str(root/'accounts'),api_token='');agent=Agent(settings)
                with module.serve(accounts_app(settings,agent=agent)) as accounts:
                    write_private_new(root/'audit.key',secrets.token_urlsafe(48))
                    bridge_config=BridgeConfig(accounts,inference,str(root/'model.key'),str(root/'control.sqlite3'),audit_key_file=str(root/'audit.key'),job_timeout=180,openclaw_url=url,openclaw_private_key_file=str(home/'device.pem'),openclaw_device_token_file=str(home/'device.token'))
                    with module.serve(bridge_app(bridge_config)) as bridge_origin,httpx.Client(base_url=accounts,timeout=10,trust_env=False) as account:
                        password=secrets.token_urlsafe(32)
                        account.post('/api/account/register',json={'username':'owner','display_name':'Native Owner','password':password}).raise_for_status()
                        agent.admin.initialize('owner',root/'owner.key')
                        account.post('/api/admin/unlock',json={'code':(root/'owner.key').read_text().strip()}).raise_for_status()
                        enrollment=account.post('/api/admin/mfa/setup',json={'password':password});enrollment.raise_for_status()
                        account.post('/api/admin/mfa/confirm',json={'otp':pyotp.TOTP(enrollment.json()['secret']).now()}).raise_for_status()
                        with httpx.Client(base_url=bridge_origin,cookies={'zenith_login':account.cookies['zenith_login']},timeout=20,trust_env=False) as bridge:
                            payload={'message':'What is 2 plus 2? Answer with the number only.','conversation_id':'arithmetic'}
                            body={'runtime':'openclaw','operation':'chat','payload':payload}
                            check(bridge.post('/v1/jobs',json=body,headers={'Idempotency-Key':'denied_native_turn'}).status_code==403,'Owner grant was not required')
                            scope={'runtime':'openclaw','operation':'chat',**chat_scope(payload,'chat')}
                            granted=bridge.post('/v1/grants',json={'capability':'jobs.submit.openclaw','seconds':240,'scope':scope});granted.raise_for_status();body['grant_id']=granted.json()['id']
                            started=time.monotonic();admitted=bridge.post('/v1/jobs',json=body,headers={'Idempotency-Key':'real_native_turn'});admitted.raise_for_status();job=admitted.json()['id']
                            check(bridge.post('/v1/jobs',json=body,headers={'Idempotency-Key':'real_native_turn'}).json()['id']==job,'Native turn was duplicated')
                            deadline=time.monotonic()+200
                            while True:
                                response=bridge.get('/v1/jobs/'+job);response.raise_for_status();state=response.json()
                                if state['status'] in {'succeeded','failed','cancelled','interrupted'}:break
                                check(time.monotonic()<deadline,'Native turn exceeded deadline');time.sleep(.2)
                            report['bridge_job']={'status':state['status'],'seconds':time.monotonic()-started,'error_code':state.get('error_code'),'native_receipt':state.get('native_receipt')}
                            check(state['status']=='succeeded','Real native OpenClaw turn failed')
                            response=bridge.get('/v1/jobs/'+job+'/result');response.raise_for_status();result=response.json()['result']['result']
                            report['native_final_state']=result['state'];report['message']=result.get('message')
                            check(result['state']=='final' and len(metrics)>0,'No actual Zenith inference was measured')
                            report['measured_model_calls']=metrics
                            account.post('/api/account/logout').raise_for_status()
                            report['logout_revokes_bridge']=bridge.get('/healthz').status_code==401
                            check(report['logout_revokes_bridge'],'Original logout did not revoke bridge access')
            finally:
                process.terminate()
                try:process.wait(20)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                report['original_model_artifacts_unchanged']=verify(root/'identity.json')[1]==identity
                report['tracked_upstream_source_unchanged']=subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD']).returncode==0
                report['native_gateway_cleanly_exited']=process.returncode==0
                args.output.write_text(json.dumps(report,indent=2)+'\n')
        check(report['original_model_artifacts_unchanged'] and report['tracked_upstream_source_unchanged'],'Original artifacts changed')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native-root',type=Path,required=True);parser.add_argument('--node',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
