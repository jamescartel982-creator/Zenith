"""Read-only preserved-checkpoint baseline. Writes reports only to a new directory."""
import argparse,hashlib,json,resource,subprocess,tempfile,time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Use a new report path')
    from agent.config import Settings
    from agent.paths import config_file
    from agent.checkpoints import load_existing,tokenizer_signature
    from agent.providers import HuggingFaceProvider
    from agent.core import Agent
    from agent.quality import DEFAULT_SUITE,score_case,summarize,configuration_signature
    from agent.model_registry import build_registry
    from agent.orchestration import Orchestrator
    from agent.reasoning import ReasoningEngine
    from agent.planning import ReasoningBudget
    from agent.task_router import RoutingRequest
    from scripts.inference_speed_benchmark import validate_selection,parameter_hash
    from zenith_inference.identity import verify
    original=Settings();identity,digest=verify(args.identity);validate_selection(original,identity)
    profile=config_file();profile_digest=hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None
    settings=replace(original,offline=True,device='cpu',temperature=0,max_new_tokens=64,fast_max_new_tokens=64,calibration_file='')
    started=time.perf_counter();model,tokenizer,details=load_existing(settings.adapter,cpu_threads=settings.cpu_threads)
    load_seconds=time.perf_counter()-started
    assert tokenizer_signature(tokenizer)==identity['tokenizer_sha256']
    before_parameters=parameter_hash(model)
    provider=HuggingFaceProvider(settings);provider.model,provider.tokenizer=model,tokenizer
    report={'schema_version':1,'purpose':'Read-only current-system audit baseline; no candidate upgrade or model promotion',
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'identity_sha256':digest,'model':settings.model,'revision':settings.revision,
        'configuration_sha256':configuration_signature(settings,'fast'),
        'configuration':{'temperature':0,'max_new_tokens':64,'context_tokens':settings.context_tokens,'cpu_threads':settings.cpu_threads,'device':'cpu'},
        'architecture':{k:details[k] for k in ('model_type','architecture','base_parameters','total_parameters_with_adapter','layers','hidden_size','attention_heads','kv_heads','context_limit','embedding_vocabulary','tokenizer_size','tokenizer_sha256','checkpoint_format','framework')},
        'checkpoint_files':{k:v for k,v in details['parent_files'].items()},
        'training_summary':{k:details['training_history'].get(k) for k in ('base_model','base_revision','objective','train_examples','eval_examples','seed','promoted','automatic_promotion','weights_reinitialized')},
        'trained_adapter_nonzero_and_finite':True,'strict_checkpoint_load_seconds':load_seconds,
        'gpu_available':False,'gpu_utilization':None,'gpu_peak_memory_bytes':None,'gpu_reason':'CPU-only container; no GPU benchmark performed'}
    start=time.perf_counter();warm,_=provider.generate([{'role':'user','content':'Reply with exactly READY.'}])
    report['warmup']={'text':warm,'elapsed_ms':(time.perf_counter()-start)*1000}
    try:
        suite=json.loads(DEFAULT_SUITE.read_text());results=[]
        with tempfile.TemporaryDirectory(prefix='zenith-audit-diagnostic-') as directory:
            app=Agent(replace(settings,data_dir=directory),provider)
            for case in suite['cases']:
                start=time.perf_counter();answer=app.answer(case['prompt'],str(uuid4()),response_mode='fast')
                row={'id':case['id'],'prompt':case['prompt'],'response':answer['response'],'latency_ms':(time.perf_counter()-start)*1000,
                    'first_text_ms':answer['time_to_first_text_ms'],'should_abstain':case['should_abstain'],
                    'slices':case['slices']+['path:'+answer['quality']['method']], 'quality':answer['quality'],'performance':answer['performance']}
                row.update(score_case(case,row['response']));results.append(row)
                print(json.dumps({'diagnostic':case['id'],'passed':row['passed'],'method':answer['quality']['method']}),flush=True)
        report['application_diagnostics']={'suite_sha256':hashlib.sha256(DEFAULT_SUITE.read_bytes()).hexdigest(),'results':results,'slices':summarize(results)}
        suitepath=Path('agent/evaluation/reasoning-v1.json');suite=json.loads(suitepath.read_text())
        registry=build_registry(settings);registry.adapters['huggingface'].providers[registry.native_key]=provider
        engine=ReasoningEngine(Orchestrator(registry));results=[]
        for case in suite['cases']:
            messages=[{'role':'system','content':'You are Zenith. Follow the requested format exactly.'},{'role':'user','content':case['prompt']}]
            start=time.perf_counter();answer,_=provider.generate(messages);baseline_ms=(time.perf_counter()-start)*1000
            start=time.perf_counter();reasoned,trace=engine.run(messages,ReasoningBudget('standard',max_calls=4,max_output_tokens=64,timeout=120),RoutingRequest(max_calls=4,max_output_tokens=64),expression=case.get('expression'))
            row={'id':case['id'],'expected':case['expected'],'native':answer,'reasoned':reasoned.text,
                'native_passed':answer==case['expected'],'reasoning_passed':reasoned.text==case['expected'],
                'native_ms':baseline_ms,'reasoning_ms':(time.perf_counter()-start)*1000,'trace':trace,'usage':reasoned.usage}
            results.append(row);print(json.dumps({'reasoning':case['id'],'native_passed':row['native_passed'],'reasoning_passed':row['reasoning_passed']}),flush=True)
        report['reasoning_diagnostics']={'suite_sha256':hashlib.sha256(suitepath.read_bytes()).hexdigest(),'results':results,'native_correct':sum(r['native_passed'] for r in results),'reasoning_correct':sum(r['reasoning_passed'] for r in results)}
        after=verify(args.identity)[1]
        assert after==digest and parameter_hash(model)==before_parameters
        assert (hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None)==profile_digest
        report.update(peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            runtime_parameter_sha256=before_parameters,checkpoint_and_profile_unchanged=True,runtime_parameters_unchanged=True,
            external_model_calls=0,limitations=['Public authored development diagnostics, not sealed generalization tests','Application scores include deterministic checks; model-only slices are reported separately','One observation per case/path; no improvement claim','Peak RSS includes loading, finite-weight validation and inference','No GPU, broad multimodal, sandbox-escape or live external-provider benchmarks'])
        with args.output.open('x') as output:json.dump(report,output,indent=2);output.write('\n')
        print(json.dumps({'output':str(args.output),'application_accuracy':report['application_diagnostics']['slices']['all']['accuracy'],'reasoning_correct':report['reasoning_diagnostics']['reasoning_correct'],'peak_rss_kib':report['peak_process_rss_kib']}),flush=True)
    finally:provider.close()
if __name__=='__main__':main()
