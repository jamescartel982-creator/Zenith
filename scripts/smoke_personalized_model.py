"""Actual preserved-model/account/preferences acceptance; no training or promotion."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from uuid import uuid4


def measure(identity,generated=False):
    from fastapi.testclient import TestClient
    from agent.config import Settings
    from agent.paths import config_file
    from agent.checkpoints import load_existing
    from agent.core import Agent
    from agent.server import create_app
    from agent.model_metrics import parameter_inventory
    from scripts.inference_speed_benchmark import validate_selection,parameter_hash
    from zenith_inference.identity import verify
    original=Settings();record,before=verify(identity);validate_selection(original,record)
    profile=config_file();old=hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None
    with tempfile.TemporaryDirectory(prefix='zenith-personalized-model-') as folder:
        settings=replace(original,data_dir=folder,offline=True,device='cpu',temperature=0,max_new_tokens=32,fast_max_new_tokens=32,knowledge_limit=0,api_token='',calibration_file='')
        agent=Agent(settings)
        model,tokenizer,details=load_existing(settings.adapter,cpu_threads=settings.cpu_threads)
        agent.provider.model,agent.provider.tokenizer=model,tokenizer
        parameters=parameter_hash(model);counts=parameter_inventory(agent.provider)
        assert counts['total']==details['total_parameters_with_adapter']
        assert counts['base']==details['base_parameters']
        calls=[0]
        def forward(*args,**kwargs):calls[0]+=1
        hook=model.get_base_model().register_forward_pre_hook(forward)
        try:
            with TestClient(create_app(settings,agent),base_url='http://127.0.0.1') as client:
                client.post('/api/account/register',json={'username':'personal-test','display_name':'Test','password':'temporary isolated test account password'}).raise_for_status()
                analysis=client.post('/api/analysis/csv',json={'csv_text':'value\n0.1\n0.2\n'})
                analysis.raise_for_status();assert calls[0]==0
                assert analysis.json()['column_summaries'][0]['sum']=='0.3'
                client.put('/api/preferences',json={'values':{'language':'fr','tone':'friendly','reply_style':'brief'}}).raise_for_status()
                session=str(uuid4())
                answer=client.post('/api/chat',json={'session_id':session,'message':'Greet me using my saved language preference. Return one word.'})
                answer.raise_for_status();result=answer.json()
                greeting=result['response'].strip().strip('!.,').casefold()
                assert greeting in {'bonjour','salut','coucou'},result['response']
                assert calls[0]>0
                with agent.store.connect() as db:
                    messages=json.loads(db.execute('SELECT messages FROM turns WHERE session_id=?',(session,)).fetchone()[0])
                assert 'French' in messages[0]['content']
                client.delete('/api/preferences').raise_for_status()
                assert client.get('/api/preferences').json()['values']=={}
                recipe_answer = None
                if generated:
                    from agent.recipe_catalog import RecipeCatalog
                    receipt = RecipeCatalog(agent.store).install(True)
                    assert receipt['installed'] == 100000
                    assert client.get('/api/skills/profile/x-recipes-90000').status_code == 403
                    client.post('/api/skills/command',json={'session_id':session,'command':'/skill x-recipes-25000'}).raise_for_status()
                    recipe_answer = client.post('/api/chat',json={'session_id':session,
                        'message':'What does Python print(2+2) print? Return only the number.'})
                    recipe_answer.raise_for_status();recipe_answer=recipe_answer.json()
                    assert recipe_answer['response'].strip()=='4',recipe_answer['response']
                    with agent.store.connect() as db:
                        recipe_context = json.loads(db.execute('SELECT messages FROM turns WHERE session_id=? ORDER BY rowid DESC',(session,)).fetchone()[0])
                    assert 'Generated workflow recipe; not independently evaluated' in recipe_context[0]['content']
            assert verify(identity)[1]==before and parameter_hash(model)==parameters
            assert (hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None)==old
            return {'preserved_identity_sha256':before,'parameter_inventory':counts,
                'runtime_parameter_sha256':parameters,'csv_exact_decimal_sum':'0.3','csv_model_forward_calls':0,
                'saved_language_response':result['response'],'real_model_calls':result['performance']['usage']['model_calls'],
                'generated_recipe_response':recipe_answer['response'] if recipe_answer else None,
                'generated_recipe_model_calls':recipe_answer['performance']['usage']['model_calls'] if recipe_answer else 0,
                'generated_recipes_installed_in_test':100000 if generated else 0,
                'preferences_removed':True,'original_checkpoint_and_profile_unchanged':True,
                'limitations':['One greeting verifies this configured model/task, not universal multilingual/accuracy improvement.',
                    'Skills are instruction profiles; no weights, architecture or tokenizer changed.']}
        finally:hook.remove();agent.provider.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--identity',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--generated-recipes',action='store_true');args=parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    args.output=check_destination(Settings(),config_file(),args.output)
    report=measure(args.identity,args.generated_recipes)
    with args.output.open('x') as handle:json.dump(report,handle,indent=2);handle.write('\n')
    print(json.dumps(report,indent=2))
