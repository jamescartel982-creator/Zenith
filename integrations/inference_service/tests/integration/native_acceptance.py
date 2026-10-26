"""Real TCP/OpenAI SDK/account/job acceptance; never uses a scripted model."""
import argparse
import faulthandler
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
import secrets
import socket
import tempfile
import threading
import time


def check(condition, message):
    if not condition:
        raise AssertionError(message)


@contextmanager
def serve(app):
    import uvicorn
    listener = socket.socket()
    listener.bind(('127.0.0.1',0))
    listener.listen(16)
    origin = 'http://127.0.0.1:'+str(listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', access_log=False, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets':[listener]}, daemon=False)
    thread.start()
    try:
        deadline = time.monotonic()+10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        check(server.started,'Real service did not start')
        yield origin
    finally:
        server.should_exit=True
        thread.join(20)
        if thread.is_alive():
            server.force_exit=True
            thread.join(5)
        listener.close()
        check(not thread.is_alive(),'Service worker did not shut down')


def run(output):
    # Test-only stacks contain no request payloads or secret values. Capture a
    # genuine platform stall instead of silently increasing timeouts or skipping.
    faulthandler.dump_traceback_later(45, repeat=True)
    import httpx
    import openai
    from openai import OpenAI
    from agent.config import Settings
    from agent.paths import config_file
    from agent.core import Agent
    from agent.server import create_app as native_app
    from zenith_inference.backend import NativeBackend
    from zenith_inference.identity import capture, verify, sha256
    from zenith_inference.limits import Limits
    from zenith_inference.server import create_app as model_app
    from zenith_integrations.config import BridgeConfig
    from zenith_integrations.gateway import create_app as bridge_app
    from zenith_integrations.shared.authorization import ServiceAuth
    from zenith_integrations.shared.secrets import write_private_new
    settings=Settings()
    print('Native acceptance: loading the verified trained checkpoint', flush=True)
    profile=config_file()
    prior_profile=sha256(profile) if profile.is_file() else None
    report={'openai_sdk':openai.__version__,'scripted_model':False,'live_execution':False}
    with tempfile.TemporaryDirectory(prefix='Zenith real bridge acceptance ') as folder:
        root=Path(folder)
        key=secrets.token_urlsafe(48)
        key_file=root/'inference.key'
        write_private_new(key_file,key+'\n')
        manifest=root/'identity.json'
        capture(settings,manifest)
        backend=NativeBackend(manifest,Limits(settings.context_tokens,256,120))
        backend.load()
        report.update(identity_sha256=backend.identity_hash,tokenizer_sha256=backend.record['tokenizer_sha256'])
        auth=ServiceAuth([{'id':'acceptance','token_file':str(key_file),'models':['zenith'],
                          'capabilities':['inference.read','inference.generate']}])
        with serve(model_app(backend,auth)) as inference:
            client=OpenAI(base_url=inference+'/v1',api_key=key,max_retries=0,timeout=120)
            check([m.id for m in client.models.list().data]==['zenith'],'Model discovery failed')
            prompt=[{'role':'user','content':'What is 2 plus 2? Answer with the number only.'}]
            started=time.perf_counter()
            print('Native acceptance: synchronous SDK chat', flush=True)
            completion=client.chat.completions.create(model='zenith',messages=prompt,max_tokens=16,temperature=0)
            elapsed=time.perf_counter()-started
            check(completion.choices[0].message.content.strip()=='4','Real checkpoint arithmetic regression')
            report['chat']={'answer':completion.choices[0].message.content,'usage':completion.usage.model_dump(),'seconds':elapsed}
            print('Native acceptance: streamed SDK chat', flush=True)
            chunks=list(client.chat.completions.create(model='zenith',messages=prompt,max_tokens=16,
                        stream=True,stream_options={'include_usage':True},temperature=0))
            streamed=''.join(c.choices[0].delta.content or '' for c in chunks if c.choices)
            check(streamed.strip()=='4','Real streaming regression')
            check(any(c.usage and c.usage.completion_tokens > 0 for c in chunks),'Missing actual token counts')
            report['stream']={'answer':streamed,'usage_present':True}
            tool={'type':'function','function':{'name':'add','description':'Add two integers.',
                'parameters':{'type':'object','properties':{'a':{'type':'integer'},'b':{'type':'integer'}},
                              'required':['a','b'],'additionalProperties':False}}}
            question={'role':'user','content':'Use the add tool to add 2 and 2. You must call add, do not calculate directly.'}
            print('Native acceptance: generated tool call after streaming', flush=True)
            call_response=client.chat.completions.create(model='zenith',messages=[question],tools=[tool],
                        tool_choice='required',max_tokens=128,temperature=0)
            message=call_response.choices[0].message
            check(bool(message.tool_calls),'Existing checkpoint did not produce a real tool call')
            check(len(message.tool_calls)==1,'Unexpected tool multiplicity')
            call=message.tool_calls[0]
            check(call.function.name=='add' and json.loads(call.function.arguments)=={'a':2,'b':2},'Real tool call was incorrect')
            # The allowlisted test executor supplies the result; inference runs no tools.
            print('Native acceptance: native tool-result conversation', flush=True)
            result=client.chat.completions.create(model='zenith',messages=[question,message.model_dump(exclude_none=True),
                {'role':'tool','tool_call_id':call.id,'content':'4'}],tools=[tool],max_tokens=64,temperature=0)
            check('4' in (result.choices[0].message.content or ''),'Native tool-result history failed')
            report['tool_round_trip']={'name':'add','arguments':{'a':2,'b':2},'answer':result.choices[0].message.content,
                                      'executor':'explicit allowlisted test fixture; inference executed no tool'}
            # Disconnect a real streaming TCP client, then verify model admission recovers.
            print('Native acceptance: TCP disconnect and recovery', flush=True)
            stream=client.chat.completions.create(model='zenith',messages=[{'role':'user','content':'Count from 1 to 100, one number per line.'}],
                                                 stream=True,max_tokens=256,temperature=0)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    break
            stream.close()
            deadline=time.monotonic()+10
            while True:
                try:
                    again=client.chat.completions.create(model='zenith',messages=prompt,max_tokens=16,temperature=0)
                    check(again.choices[0].message.content.strip()=='4','Inference failed after disconnect')
                    break
                except openai.RateLimitError:
                    check(time.monotonic()<deadline,'Model worker did not recover after client disconnect')
                    time.sleep(0.05)
            report['disconnect_recovery']=True
            print('Native acceptance: real accounts and durable jobs', flush=True)
            # Reuse original native account/session APIs in a new, isolated test profile.
            account_settings=replace(settings,data_dir=str(root/'native-account-data'),api_token='')
            native_agent=Agent(account_settings)
            with serve(native_app(account_settings,agent=native_agent)) as zenith:
                bridge_dir=root/'bridge'
                bridge_dir.mkdir(mode=0o700)
                write_private_new(bridge_dir/'audit.key',secrets.token_urlsafe(48)+'\n')
                config=BridgeConfig(zenith,inference,str(key_file),str(bridge_dir/'control.sqlite3'),audit_key_file=str(bridge_dir/'audit.key'))
                with serve(bridge_app(config)) as bridge:
                    with httpx.Client(base_url=zenith,timeout=10) as session:
                        response=session.post('/api/account/register',json={'username':'acceptance','display_name':'Acceptance',
                            'password':secrets.token_urlsafe(32)})
                        check(response.status_code==200,'Native account creation failed')
                        cookie=session.cookies.get('zenith_login')
                        with httpx.Client(base_url=bridge,cookies={'zenith_login':cookie},timeout=10) as gateway:
                            payload={'runtime':'zenith','operation':'chat','payload':{'model':'zenith','messages':prompt,'max_tokens':16,'temperature':0}}
                            request_key=secrets.token_hex(16)
                            admitted=gateway.post('/v1/jobs',json=payload,headers={'Idempotency-Key':request_key})
                            check(admitted.status_code==202,'Authenticated bridge admission failed')
                            identifier=admitted.json()['id']
                            duplicate=gateway.post('/v1/jobs',json=payload,headers={'Idempotency-Key':request_key})
                            check(duplicate.json()['id']==identifier,'Duplicate work was admitted')
                            deadline=time.monotonic()+120
                            while True:
                                state=gateway.get('/v1/jobs/'+identifier).json()
                                if state['status'] in {'succeeded','failed','interrupted','cancelled'}:
                                    break
                                check(time.monotonic()<deadline,'Bridge job did not finish')
                                time.sleep(0.05)
                            check(state['status']=='succeeded','Real bridge job failed')
                            result=gateway.get('/v1/jobs/'+identifier+'/result').json()['result']
                            check(result['choices'][0]['message']['content'].strip()=='4','Bridge returned the wrong real-model result')
                            report['real_bridge_job']={'status':state['status'],'answer':'4','duplicate_admission_prevented':True}
                            session.post('/api/account/logout')
                            check(gateway.get('/v1/jobs/'+identifier).status_code==401,'Revoked native login retained access')
                            report['logout_revocation']=True
            client.close()
        check(verify(manifest)[1]==backend.identity_hash,'Original artifacts changed during inference')
    check((sha256(profile) if profile.is_file() else None)==prior_profile,'Production profile changed')
    report['original_artifacts_unchanged']=True
    report['production_profile_unchanged']=True
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    try:
        run(parser.parse_args().output)
    finally:
        faulthandler.cancel_dump_traceback_later()
