"""Run installed setup, experimental inference, and exact rollback in a private profile."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check(bundle):
    bundle=Path(bundle).resolve()
    with tempfile.TemporaryDirectory(prefix='Zenith experimental activation ') as folder:
        root=Path(folder);profile=root/'config.env'
        original=b'AI_PROVIDER=ollama\nPRESERVED_SETTING=yes\n';profile.write_bytes(original)
        environment=os.environ.copy()
        for key in ['AI_PROVIDER','HF_MODEL','HF_REVISION','ZENITH_ADAPTER','ZENITH_CHECKPOINT_RECEIPT','ZENITH_TEAM_CONFIG','AGENT_DATA_DIR','PYTHONPATH']:
            environment.pop(key,None)
        environment.update(ZENITH_HOME=str(root),ZENITH_CONFIG_FILE=str(profile),HF_HUB_OFFLINE='1')
        def run(*args):
            return subprocess.check_output([sys.executable,'-I','-m','agent',*args],cwd=root,env=environment,text=True,encoding='utf-8')
        run('setup','--activate-candidate','--bundle',str(bundle))
        status=json.loads(run('deployment','status'))
        receipt=json.loads(Path(status['receipt']).read_text(encoding='utf-8'))
        if receipt['numeric_gate_passed'] or not receipt['regression_override'] or receipt['activation_status']!='experimental':
            raise AssertionError('Experimental activation did not preserve the failed quality gate')
        code='''import json
from agent.config import Settings
from agent.providers import HuggingFaceProvider,SYSTEM_PROMPT
from dataclasses import replace
s=replace(Settings(),temperature=0,max_new_tokens=32,cpu_threads=2,offline=True)
p=HuggingFaceProvider(s)
a,_=p.generate([{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':'Which planet is known as the Red Planet? Answer with the planet name.'}])
print(json.dumps({'answer':a,'active_adapter':s.adapter,'receipt':s.checkpoint_receipt}))
'''
        response=json.loads(subprocess.check_output([sys.executable,'-I','-c',code],cwd=root,env=environment,text=True,encoding='utf-8'))
        if 'mars' not in response['answer'].casefold():raise AssertionError('Experimental installed-provider inference failed')
        if Path(response['active_adapter']).resolve()!=Path(receipt['candidate']).resolve():raise AssertionError('Saved model was not selected')
        run('deployment','rollback','--receipt',status['receipt'])
        if profile.read_bytes()!=original:raise AssertionError('Rollback did not restore the exact prior profile')
        return {'setup_cli_verified':True,'activation_status':receipt['activation_status'],
            'numeric_gate_passed':False,'regression_override':True,'inference':response['answer'],
            'restricted_tools_enabled':receipt['network_tools_enabled'],'rollback_verified':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True)
    print(json.dumps(check(parser.parse_args().bundle),indent=2))


if __name__=='__main__':main()
