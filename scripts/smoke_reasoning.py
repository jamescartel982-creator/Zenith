"""Real unchanged-checkpoint baseline/reasoning diagnostics with frozen cases."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time
from agent.checkpoints import inventory
from agent.config import Settings
from agent.model_registry import build_registry
from agent.orchestration import Orchestrator
from agent.paths import config_file
from agent.planning import ReasoningBudget
from agent.providers import HuggingFaceProvider
from agent.reasoning import ReasoningEngine
from agent.task_router import RoutingRequest

SUITE = Path(__file__).resolve().parents[1] / 'agent' / 'evaluation' / 'reasoning-v1.json'


def check():
    suite_bytes=SUITE.read_bytes(); suite=json.loads(suite_bytes)
    settings=replace(Settings(),provider='huggingface',temperature=0,max_new_tokens=64,offline=True)
    previous=inventory(settings.adapter) if settings.adapter else None
    profile=config_file(); profile_bytes=profile.read_bytes() if profile.exists() else None
    provider=HuggingFaceProvider(settings); started=time.perf_counter();provider.load();cold=time.perf_counter()-started
    registry=build_registry(settings)
    registry.adapters['huggingface'].providers[registry.native_key]=provider
    engine=ReasoningEngine(Orchestrator(registry)); rows=[]
    for case in suite['cases']:
        messages=[{'role':'system','content':'You are Zenith. Follow the requested format exactly.'},{'role':'user','content':case['prompt']}]
        start=time.perf_counter(); baseline,_=provider.generate(messages); original_ms=(time.perf_counter()-start)*1000
        result,trace=engine.run(messages,ReasoningBudget('standard',max_calls=4,max_output_tokens=64,timeout=120),
            RoutingRequest(max_calls=4,max_output_tokens=64),expression=case.get('expression'))
        rows.append({'id':case['id'],'expected':case['expected'],'baseline_response':baseline,'reasoning_response':result.text,
            'baseline_passed':baseline==case['expected'],'reasoning_passed':result.text==case['expected'],
            'baseline_ms':round(original_ms,3),'reasoning':trace,'usage':result.usage})
    if previous is not None and inventory(settings.adapter)!=previous:raise AssertionError('Original checkpoint changed')
    if (profile.read_bytes() if profile.exists() else None)!=profile_bytes:raise AssertionError('Saved profile changed')
    return {'schema_version':1,'suite_sha256':hashlib.sha256(suite_bytes).hexdigest(),'model':settings.model,'revision':settings.revision,
        'adapter_sha256':previous['adapter_model.safetensors']['sha256'] if previous else None,'device':str(provider.model.device),
        'cold_load_seconds':round(cold,3),'configuration':{'temperature':0,'max_output_tokens':64,'cpu_threads':settings.cpu_threads,'reasoning_effort':'standard'},
        'baseline_correct':sum(r['baseline_passed'] for r in rows),'reasoning_correct':sum(r['reasoning_passed'] for r in rows),'cases':len(rows),
        'results':rows,'weights_unchanged':True,'profile_unchanged':True,'external_calls':0,
        'limitations':['Small public authored fixture; not a broad reasoning/coding benchmark or evidence of frontier parity.',
            'One sample per task/path; no statistically supported performance gain is claimed.',
            'Arithmetic constraints and model-review tokens are harness costs, not additional model training.',
            'No GPU, paid API, TTFT, calibrated confidence or general Python sandbox results are claimed.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=check(); value=json.dumps(report,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as stream:stream.write(value)
    print(value)


if __name__=='__main__':main()
