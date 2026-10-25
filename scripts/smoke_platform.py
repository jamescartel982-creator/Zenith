"""Real loopback HTTP server: authenticated queued task, event replay and shutdown.

The arithmetic answer deliberately uses Zenith's existing deterministic path.
Run platform_benchmark separately for actual selected-checkpoint inference.
"""
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time

import requests


def main():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0)); port=listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='zenith-platform-http-') as folder, tempfile.TemporaryFile() as log:
        token=secrets.token_urlsafe(32)
        environment={**os.environ,'AGENT_DATA_DIR':folder,'AI_PROVIDER':'huggingface','ZENITH_API_TOKEN':token,
                     'ZENITH_PLATFORM_ENABLED':'true','ZENITH_PLATFORM_RUNTIME_ENABLED':'true',
                     'ZENITH_PLATFORM_TOOLS_ENABLED':'false','ZENITH_PLATFORM_MEMORY_ENABLED':'false'}
        process=subprocess.Popen([sys.executable,'-m','agent','serve','--port',str(port)],
                                 env=environment,stdout=log,stderr=subprocess.STDOUT)
        url=f'http://127.0.0.1:{port}'
        try:
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError('Platform HTTP server exited during startup')
                try:
                    response=requests.get(url+'/healthz',timeout=1)
                    if response.status_code==200:break
                except requests.RequestException:pass
                time.sleep(0.1)
            else:raise RuntimeError('Platform HTTP startup timed out')
            with requests.Session() as client:
                client.headers['Authorization']='Bearer '+token
                assert client.get(url+'/api/platform/status',timeout=3).status_code==401
                response=client.post(url+'/api/account/register',json={'username':'http-fixture','display_name':'Fixture',
                    'password':secrets.token_urlsafe(24)},timeout=5)
                response.raise_for_status()
                status=client.get(url+'/api/platform/status',timeout=3).json()
                assert status['worker_running'] and not status['tools_enabled']
                response=client.post(url+'/api/platform/tasks',json={'kind':'chat','message':'What is 2 plus 2?'},timeout=5)
                response.raise_for_status(); identifier=response.json()['id']
                for _ in range(100):
                    response=client.get(url+'/api/platform/tasks/'+identifier,timeout=3)
                    response.raise_for_status(); task=response.json()
                    if task['status'] in {'completed','failed','cancelled','needs_reconciliation'}:break
                    time.sleep(0.05)
                assert task['status']=='completed' and task['result']['response']=='4',task['status']
                response=client.get(url+f'/api/platform/tasks/{identifier}/events',timeout=5)
                response.raise_for_status();assert 'event: platform-event' in response.text
                assert token not in response.text
                assert client.get(url+'/api/platform/audit/verify',timeout=3).status_code==403
            assert requests.get(url+'/api/platform/status',timeout=3).status_code==401
            print(json.dumps({'real_loopback_http':True,'authenticated_task':'completed','response':'4',
                              'event_replay':True,'tools_disabled':True,'model_calls':0}))
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


if __name__=='__main__':main()
