"""Exercise approved-bundle activation, real installed inference, and rollback."""
import argparse
import json
from pathlib import Path
import tempfile
from agent.config import Settings
from agent.deployment import use_release,rollback
from agent.providers import HuggingFaceProvider,SYSTEM_PROMPT


def check(bundle):
    with tempfile.TemporaryDirectory(prefix='Zenith model release ') as folder:
        root=Path(folder);profile=root/'config.env';original=b'AI_PROVIDER=ollama\nPRESERVED_SETTING=yes\n';profile.write_bytes(original)
        receipt=use_release(bundle,True,profile,root/'deployments',root/'models','Ephemeral CI profile; real loading and inference verification.')
        receipt_path=root/'deployments'/receipt['id']/'receipt.json'
        settings=Settings(provider='huggingface',model=receipt['base_model'],revision=receipt['base_revision'],
            adapter=receipt['candidate'],checkpoint_receipt=str(receipt_path),temperature=0,offline=True,max_new_tokens=32,cpu_threads=2)
        provider=HuggingFaceProvider(settings)
        answer,_=provider.generate([{'role':'system','content':SYSTEM_PROMPT},
            {'role':'user','content':'Which planet is known as the Red Planet? Answer with the planet name.'}])
        if 'mars' not in answer.casefold():raise AssertionError('Activated checkpoint failed installed-provider inference')
        del provider
        import gc;gc.collect()
        rollback(receipt_path)
        if profile.read_bytes()!=original:raise AssertionError('Rollback did not restore the exact previous profile')
        return {'activated_in_ephemeral_profile':True,'real_inference_answer':answer,'rollback_verified':True,'restricted_tools_enabled':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True)
    print(json.dumps(check(parser.parse_args().bundle),indent=2))


if __name__=='__main__':main()
