"""Check an image's installed package and persistent accounts/code across recreation.

Creates uniquely named temporary containers/volume, then removes only those.
Optional --hf-cache points to an existing Hugging Face hub cache for real inference.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import requests


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',default='zenith:ci');parser.add_argument('--hf-cache',type=Path);args=parser.parse_args()
    environment=os.environ.copy()
    for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):environment.pop(key,None)
    environment['ZENITH_API_TOKEN']=secrets.token_urlsafe(32)
    docker=['docker','--host='+('npipe:////./pipe/docker_engine' if os.name=='nt' else 'unix:///var/run/docker.sock')]
    def call(parts):return subprocess.check_output([*docker,*parts],env=environment,text=True,stderr=subprocess.STDOUT)
    identifier=secrets.token_hex(6);name='zenith-check-'+identifier;volume=name+'-data'
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    session=requests.Session();session.trust_env=False;session.headers['Authorization']='Bearer '+environment['ZENITH_API_TOKEN']
    url=f'http://127.0.0.1:{port}'
    def api(method,path,body=None):
        response=session.request(method,url+path,json=body,timeout=30);response.raise_for_status();return response.json()
    def start():
        command=['run','-d','--name',name,'-p',f'127.0.0.1:{port}:7860','-v',volume+':/app/data',
                 '-e','ZENITH_API_TOKEN','-e','AI_PROVIDER='+('ensemble' if args.hf_cache else 'localserver'),
                 '-e','ZENITH_CPU_THREADS=2','-e','HF_HUB_OFFLINE=1']
        if args.hf_cache:command+=['--mount',f'type=bind,src={args.hf_cache.resolve()},dst=/home/zenith/.cache/huggingface/hub,readonly']
        call([*command,args.image])
        deadline=time.monotonic()+45
        while True:
            try:
                if api('GET','/healthz')['status']=='ok':break
            except requests.RequestException:
                if time.monotonic()>deadline:raise RuntimeError('Container did not become healthy')
                time.sleep(.2)
    try:
        call(['volume','create',volume]);start()
        package=json.loads(call(['exec',name,'zenith','verify','--json']));assert package['ok']
        identity=json.loads(call(['exec',name,'python','-c','import os,json; print(json.dumps({"uid":os.getuid()}))']))
        assert identity['uid']==1000
        account=api('POST','/api/account/register',{'username':'container_owner','display_name':'Container Ada','password':'temporary container fixture password'})
        api('POST','/api/memories',{'content':'My container fixture project is Violet.'})
        call(['exec',name,'zenith','admin','init','--username','container_owner'])
        code_check='from agent.paths import zenith_home; import hashlib,json; p=zenith_home()/"admin-code.txt"; print(json.dumps({"path":str(p),"hash":hashlib.sha256(p.read_bytes()).hexdigest(),"mode":p.stat().st_mode & 511}))'
        before=json.loads(call(['exec',name,'python','-c',code_check]));assert before['path']=='/app/data/profile/admin-code.txt';assert before['mode']==384
        # Check all vendored support files are present; never run their code.
        support=json.loads(call(['exec',name,'python','-c','from agent.packs import manifests; from pathlib import Path; import json; files=[Path("/app/vendor/model-packs")/p["id"]/f["path"] for p in manifests() for f in p["files"] if f["kind"]=="support"]; assert all(f.is_file() for f in files); print(json.dumps(len(files)))']))
        assert support==43
        if args.hf_cache:
            inferred=json.loads(call(['exec',name,'zenith','doctor','--inference','--json']));assert inferred['ok'] and inferred['inference_tested']
        call(['rm','-f',name]);start()
        assert api('GET','/api/account')['user']['id']==account['user']['id']
        assert api('GET','/api/memories')['memories'][0]['content']=='My container fixture project is Violet.'
        assert api('GET','/api/admin/status')['eligible']
        after=json.loads(call(['exec',name,'python','-c',code_check]));assert after==before
        report={'version':api('GET','/healthz')['version'],'non_root':True,'wheel_verified':True,'support_files':support,
                'account_memory_and_owner_file_survive_recreation':True,'code_file_mode':'0600','real_model_inference':bool(args.hf_cache)}
        print(json.dumps(report,indent=2))
    finally:
        subprocess.run([*docker,'rm','-f',name],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run([*docker,'volume','rm',volume],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':main()
