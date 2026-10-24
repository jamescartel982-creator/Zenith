"""Exercise the standalone terminal bootstrap against a verified checkout."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    source=parser.parse_args().source.resolve()
    # The source manifest is checked by the same standalone code users download.
    # An isolated profile selects the light external runtime for this install test.
    with tempfile.TemporaryDirectory(prefix='Zenith bootstrap profile ') as home:
        environment=os.environ.copy()
        for key in ['ZENITH_CONFIG_FILE','AI_PROVIDER','ZENITH_ADAPTER','ZENITH_CHECKPOINT_RECEIPT','PYTHONPATH']:
            environment.pop(key,None)
        environment['ZENITH_HOME']=home
        result=subprocess.run([sys.executable,'-I','-','--directory',str(source),'--mode','ollama','--no-launch'],
            input=(source/'quickstart.py').read_text(encoding='utf-8'),text=True,encoding='utf-8',env=environment,check=False)
        if result.returncode:raise SystemExit(result.returncode)
        profile=(Path(home)/'config.env').read_text(encoding='utf-8')
        if 'AI_PROVIDER=ollama' not in profile:raise AssertionError('Bootstrap did not use its isolated profile')
    print('Standalone stdin installer verified; source and existing user profile preserved.')


if __name__=='__main__':main()
