"""Real local Wrangler HTTPS -> authenticated Python app acceptance; fixture model."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
from threading import Thread
import time
from uuid import uuid4


def measure(wrangler):
    import httpx
    import uvicorn
    from agent.config import Settings
    from agent.core import Agent
    from agent.cloudflare_origin import create_origin
    from agent.redaction import Redactor
    root=Path(__file__).resolve().parents[1]
    key,edge=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    class Fixture:
        model=None
        def stream(self,messages,cancel):
            for part in ('Local fixture ',edge,' complete.'):
                if cancel.is_set():return
                yield part,messages
    with tempfile.TemporaryDirectory(prefix='zenith-cloudflare-acceptance-') as folder:
        folder=Path(folder)
        settings=replace(Settings(),provider='huggingface',data_dir=str(folder/'data'),api_token=key,allowed_hosts=('127.0.0.1',))
        agent=Agent(settings,Fixture());app=create_origin(settings,agent,secret=edge)
        origin=socket.socket();origin.bind(('127.0.0.1',0));origin.listen(16)
        backend='http://127.0.0.1:'+str(origin.getsockname()[1])
        reserved=socket.socket();reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1];reserved.close()
        frontend='https://127.0.0.1:'+str(port)
        server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False,proxy_headers=False))
        thread=Thread(target=lambda:server.run(sockets=[origin]),daemon=True);thread.start()
        config=folder/'wrangler.jsonc';config.write_text(json.dumps({'name':'zenith-local-acceptance','main':str(root/'integrations/cloudflare/worker.mjs'),
            'compatibility_date':'2026-10-30','send_metrics':False,'dev':{'ip':'127.0.0.1'}}),encoding='utf-8')
        fd=os.open(folder/'.dev.vars',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as handle:handle.write('ZENITH_BACKEND_URL='+backend+'\nZENITH_ORIGIN_SECRET='+edge+'\nZENITH_TEST_LOOPBACK=1\n')
        environment=dict(os.environ,WRANGLER_SEND_METRICS='false',CLOUDFLARE_LOAD_DEV_VARS_FROM_DOT_ENV='false')
        for name in ('CLOUDFLARE_API_TOKEN','CLOUDFLARE_API_KEY','CLOUDFLARE_EMAIL','CLOUDFLARE_ACCOUNT_ID'):environment.pop(name,None)
        command=[str(wrangler),'dev','--local','--config',str(config),'--port',str(port),'--inspector-port','0','--local-protocol','https','--show-interactive-dev-session=false']
        process=None
        try:
            with (folder/'wrangler.log').open('w+') as log:
                process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=environment,cwd=folder,start_new_session=os.name=='posix')
                # The generated TLS certificate is accepted only in this
                # isolated loopback fixture. Public checks must verify TLS.
                with httpx.Client(base_url=frontend,verify=False,trust_env=False,timeout=15) as client:
                    deadline=time.monotonic()+40
                    while True:
                        try:
                            if client.get('/_edge/healthz').status_code==200:break
                        except httpx.HTTPError:pass
                        if process.poll() is not None or time.monotonic()>deadline:
                            log.seek(0);raise RuntimeError('Local Wrangler failed: '+Redactor([key,edge]).text(log.read()[-3000:]))
                        time.sleep(.1)
                    assert client.get('/healthz').status_code==200
                    assert httpx.get(backend+'/healthz',trust_env=False).status_code==403
                    page=client.get('/');page.raise_for_status();assert '<title>Zenith' in page.text
                    assert client.get('/static/app.js').text==(root/'agent/web/app.js').read_text(encoding='utf-8')
                    headers={'Origin':frontend}
                    access=client.post('/api/access',headers=headers,json={'token':key});access.raise_for_status()
                    assert 'HttpOnly' in access.headers['set-cookie'] and 'Secure' in access.headers['set-cookie']
                    client.post('/api/account/register',headers=headers,json={'username':'edge-reader','display_name':'Reader','password':'temporary isolated gateway password'}).raise_for_status()
                    assert client.get('/api/admin/help').status_code==403
                    session=str(uuid4());events=[]
                    with client.stream('POST','/api/chat/stream',headers=headers,json={'session_id':session,'message':'Explain this local fixture.'}) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if line.startswith('data: '):events.append(json.loads(line[6:]))
                    result=next(item['result'] for item in events if item['type']=='result')
                    assert result['response']=='Local fixture [REDACTED] complete.'
                    assert ''.join(item['text'] for item in events if item['type']=='delta')==result['response']
                    assert edge not in json.dumps(events) and key not in json.dumps(events)
                    assert edge not in json.dumps(agent.store.history(session))
                    assert client.post('/api/account/logout',headers={'Origin':'https://foreign.invalid'}).status_code==403
                    client.delete('/api/access',headers=headers).raise_for_status()
                    assert not any(cookie.name in {'zenith_access','zenith_login'} for cookie in client.cookies.jar)
                    assert client.get('/api/account').status_code==401
        finally:
            if process is not None:
                if process.poll() is None:
                    if os.name=='posix':os.killpg(process.pid,signal.SIGTERM)
                    else:process.terminate()
                    try:process.wait(10)
                    except subprocess.TimeoutExpired:
                        if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
                        else:process.kill()
                        process.wait(5)
            server.should_exit=True;thread.join(10);origin.close()
            if thread.is_alive():raise RuntimeError('Local origin did not stop')
    return {'real_wrangler_runtime':True,'real_python_app':True,'model':'explicit fixture; no neural quality claim',
        'frontend_bytes_preserved':True,'direct_origin_denied':True,'cookie_authentication':True,
        'server_and_owner_gates_preserved':True,'streamed_response_and_persistence_redacted':True,
        'csrf_rejected':True,'disconnect_revoked_access':True,'public_deployment_verified':False,
        'production_data_or_weights_modified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wrangler',type=Path,default=Path('node_modules/.bin/wrangler'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    destination=check_destination(Settings(),config_file(),args.output)
    executable=args.wrangler.resolve()
    if not executable.is_file():raise ValueError('Install the pinned test/deployment SDK with npm ci first')
    result=measure(executable)
    with destination.open('x',encoding='utf-8') as output:json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
