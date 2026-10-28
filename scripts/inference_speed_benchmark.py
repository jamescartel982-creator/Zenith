"""Real preserved-checkpoint latency samples; never substitutes cached answers."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time
import re
import types


def fixtures():
    from agent.providers import SYSTEM_PROMPT
    document='\n'.join(
        f'Module {index}: the sample application stores project notes locally and validates inputs before processing.'
        for index in range(55))
    return {'system':SYSTEM_PROMPT,
        'short':'What is 2 plus 2? Reply with only the number.',
        'primer':'Project reference notes follow. Treat them as background data.\n'+document+'\nReply with exactly READY.',
        'continuation':'What is 7 multiplied by 8? Reply with only the number.'}


def parameter_hash(model):
    digest=hashlib.sha256()
    for name,value in model.named_parameters():
        digest.update(name.encode());digest.update(str((tuple(value.shape),str(value.dtype))).encode())
        digest.update(memoryview(value.detach().cpu().contiguous().numpy()).cast('B'))
    return digest.hexdigest()


def baseline_provider(reference, settings, model, tokenizer):
    if not re.fullmatch(r'[a-f0-9]{40}',reference):raise ValueError('Pin the baseline to a complete Git commit')
    subprocess.run(['git','merge-base','--is-ancestor',reference,'HEAD'],check=True,capture_output=True)
    source=subprocess.check_output(['git','show',reference+':agent/providers.py'],text=True)
    module=types.ModuleType('agent._performance_baseline');module.__package__='agent'
    # Operator-selected, locally audited ancestor code. No network, arbitrary
    # path, prompt-derived source or replacement checkpoint is involved.
    exec(compile(source,'git:'+reference+':agent/providers.py','exec'),module.__dict__)
    provider=module.HuggingFaceProvider(settings)
    provider.model,provider.tokenizer=model,tokenizer
    return provider,hashlib.sha256(source.encode()).hexdigest()


def run(identity, output, samples=3, scoped_cache=False, variant='measurement', baseline_ref=None):
    from agent.config import Settings
    from agent.paths import config_file
    from agent.providers import HuggingFaceProvider
    from zenith_inference.identity import verify
    # The explicit existing identity is supplied by the operator, not discovered
    # by scanning user checkpoint or credential directories.
    record, identity_before=verify(identity)
    original=Settings()
    from scripts.platform_protection import check_destination
    output=check_destination(original,config_file(),output)
    if output.is_relative_to(Path(record['base_directory']).resolve()):raise ValueError('Keep benchmark output outside the preserved base snapshot')
    source_files=['agent/providers.py','agent/kv_cache.py','agent/config.py','agent/core.py','agent/efficiency.py','scripts/inference_speed_benchmark.py']
    source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source_files if Path(name).is_file()}
    if original.provider!='huggingface' or not original.adapter or Path(original.adapter).resolve()!=Path(record['adapter']).resolve():
        raise ValueError('Select the same existing trained model as the supplied identity')
    config=config_file()
    profile_hash=hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None
    settings=replace(original,offline=True,device='cpu',temperature=0,max_new_tokens=16)
    provider=HuggingFaceProvider(settings)
    if scoped_cache and not callable(getattr(provider,'stream_scoped',None)):
        raise ValueError('This revision does not support explicitly scoped KV reuse')
    fixture=fixtures();records=[]
    started=time.perf_counter();provider.load();load_seconds=time.perf_counter()-started
    parameters_before=parameter_hash(provider.model)
    engines={'candidate':provider};baseline_source=None
    if baseline_ref:
        engines['baseline'],baseline_source=baseline_provider(baseline_ref,settings,provider.model,provider.tokenizer)
    work={'calls':0,'input_tokens':0};cancellation_trigger=[None]
    def count_forward(module,args,kwargs):
        ids=kwargs.get('input_ids')
        if ids is not None:work['input_tokens']+=ids.shape[-1]
        elif kwargs.get('inputs_embeds') is not None:work['input_tokens']+=kwargs['inputs_embeds'].shape[-2]
        elif args:work['input_tokens']+=args[0].shape[-1]
        work['calls']+=1
        if cancellation_trigger[0] is not None:cancellation_trigger[0].set()
    hook=provider.model.get_base_model().register_forward_pre_hook(count_forward,with_kwargs=True)
    def measure(messages, scope, case, sample, engine):
        active=engines[engine];work.update(calls=0,input_tokens=0)
        started=time.perf_counter();cpu_started=time.process_time();first=None;pieces=[];cancel=threading.Event()
        stream=active.stream_scoped(messages,cancel,scope) if scoped_cache and engine=='candidate' else active.stream(messages,cancel)
        try:
            for text,used in stream:
                if first is None:first=time.perf_counter()-started
                pieces.append(text)
        finally:stream.close()
        duration=time.perf_counter()-started
        usage=dict(active.last_usage or {})
        return {'sample':sample,'case':case,'engine':engine,'elapsed_ms':duration*1000,
            'cpu_ms':(time.process_time()-cpu_started)*1000,
            'model_forward_calls':work['calls'],'forward_input_tokens':work['input_tokens'],
            'first_text_ms':first*1000 if first is not None else None,
            'response':''.join(pieces),'usage':usage,
            'output_tokens_per_second':usage['output_tokens']/duration if usage.get('output_tokens') else None}
    try:
        # Separate startup and one warm-up from the measured request samples.
        for engine in engines:
            measure([{'role':'user','content':'Reply with exactly READY.'}],('benchmark','warmup-'+engine),'warmup',0,engine)
        for index in range(samples):
            order=list(engines) if index%2==0 else list(reversed(engines))
            for engine in order:
                short=[{'role':'system','content':fixture['system']},{'role':'user','content':fixture['short']}]
                records.append(measure(short,('benchmark',engine+'-short-'+str(index)),'short',index,engine))
                scope=('benchmark',engine+'-conversation-'+str(index))
                prefix=[{'role':'system','content':fixture['system']},{'role':'user','content':fixture['primer']}]
                primer=measure(prefix,scope,'primer',index,engine);records.append(primer)
                continuation=prefix+[{'role':'assistant','content':primer['response']},{'role':'user','content':fixture['continuation']}]
                records.append(measure(continuation,scope,'continuation',index,engine))
        isolation={}
        if scoped_cache:
            prefix=[{'role':'system','content':fixture['system']},{'role':'user','content':fixture['primer']}]
            own_scope=('isolation-owner','same-session')
            first=measure(prefix,own_scope,'isolation-primer',0,'candidate')
            other=measure(prefix,('different-owner','same-session'),'other-owner',0,'candidate')
            continued=prefix+[{'role':'assistant','content':first['response']},{'role':'user','content':fixture['continuation']}]
            own=measure(continued,own_scope,'same-owner-continuation',0,'candidate')
            session=measure(prefix,('isolation-owner','different-session'),'other-session',0,'candidate')
            anonymous=measure(prefix,None,'anonymous',0,'candidate')
            isolation={'other_owner_reused_tokens':other['usage'].get('reused_input_tokens'),
                'other_session_reused_tokens':session['usage'].get('reused_input_tokens'),
                'anonymous_reused_tokens':anonymous['usage'].get('reused_input_tokens'),
                'same_owner_reused_tokens':own['usage'].get('reused_input_tokens')}
            if any(isolation[name]!=0 for name in ('other_owner_reused_tokens','other_session_reused_tokens','anonymous_reused_tokens')) or not isolation['same_owner_reused_tokens']:
                raise RuntimeError('Scoped cache isolation failed')
            changed_scope=('isolation-owner','changed-context')
            blue=[{'role':'system','content':fixture['system']},{'role':'user','content':'Project color is blue. Reply READY.'}]
            measure(blue,changed_scope,'context-primer',0,'candidate')
            red=[{'role':'system','content':fixture['system']},{'role':'user','content':'Project color is red. Reply with only the word red.'}]
            changed=measure(red,changed_scope,'changed-context',0,'candidate')
            fresh=measure(red,changed_scope,'uncached-context',0,'baseline' if baseline_ref else 'candidate')
            isolation['changed_context_parity']=changed['response']==fresh['response']
            if not isolation['changed_context_parity']:raise RuntimeError('Changed context reused stale attention state')
            if changed_scope not in provider._prefix_cache.entries:raise RuntimeError('Cancellation probe has no active cache entry')
            cancel=threading.Event();cancellation_trigger[0]=cancel;work.update(calls=0,input_tokens=0)
            try:partial=list(provider.stream_scoped(red,cancel,changed_scope))
            finally:cancellation_trigger[0]=None
            isolation.update(cancelled_during_real_forward=work['calls']>0,
                cancelled_reply_discarded=not partial,cancelled_cache_discarded=changed_scope not in provider._prefix_cache.entries)
            if not all(isolation[name] for name in ('cancelled_during_real_forward','cancelled_reply_discarded','cancelled_cache_discarded')):
                raise RuntimeError('Cancelled inference retained a reply or cache state')
        import torch
        identity_after=verify(identity)[1]
        if any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest for name,digest in source_hashes.items()):
            raise RuntimeError('Benchmark runtime source changed during measurement')
        if identity_after!=identity_before or (hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None)!=profile_hash:
            raise RuntimeError('Protected checkpoint or saved profile changed')
        parameters_after=parameter_hash(provider.model)
        if parameters_after!=parameters_before:raise RuntimeError('Runtime model parameters changed')
        medians={engine:{case:statistics.median(row['elapsed_ms'] for row in records if row['case']==case and row['engine']==engine) for case in ('short','primer','continuation')} for engine in engines}
        first_medians={engine:{case:statistics.median(row['first_text_ms'] for row in records if row['case']==case and row['engine']==engine) for case in ('short','primer','continuation')} for engine in engines}
        parity=all(next(row['response'] for row in records if row['engine']=='baseline' and row['case']==case and row['sample']==index)==next(row['response'] for row in records if row['engine']=='candidate' and row['case']==case and row['sample']==index) for index in range(samples) for case in ('short','primer','continuation')) if baseline_ref else None
        report={'variant':variant,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'provider_source_sha256':hashlib.sha256(Path('agent/providers.py').read_bytes()).hexdigest(),
            'runtime_source_sha256':source_hashes,
            'baseline_commit':baseline_ref,'baseline_provider_sha256':baseline_source,
            'fixture_sha256':hashlib.sha256(json.dumps(fixture,sort_keys=True).encode()).hexdigest(),
            'model':record['model'],'revision':record['revision'],'identity_sha256':identity_before,
            'device':'cpu','cpu_threads':settings.cpu_threads,'temperature':0,'output_token_limit':16,
            'torch':torch.__version__,'attention':provider.model.config._attn_implementation,
            'scoped_kv_reuse_requested':scoped_cache,'answer_memoization':False,
            'load_seconds':load_seconds,'samples':records,
            'medians_ms':medians,'first_text_medians_ms':first_medians,
            'exact_output_parity':parity,'runtime_parameter_sha256':parameters_before,
            'isolation_and_cancellation':isolation,
            'runtime_parameters_unchanged':True,
            'protected_artifacts_unchanged':True,
            'limitations':['Synthetic repeated project-reference context; not a general quality benchmark',
                'Provider timings exclude HTTP, retrieval, native runtimes and internet latency',
                'CPU-only small sample; no GPU or fleet-wide speedup claim']}
        with output.open('x') as handle:json.dump(report,handle,indent=2);handle.write('\n')
        print(json.dumps({'output':str(output),'variant':variant,'medians_ms':report['medians_ms']}),flush=True)
        return report
    finally:
        hook.remove()
        close=getattr(provider,'close',None)
        if close:close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=3)
    parser.add_argument('--variant',default='measurement')
    parser.add_argument('--scoped-cache',action='store_true')
    parser.add_argument('--baseline-ref',help='Explicit audited ancestor commit for an interleaved same-model comparison')
    args=parser.parse_args()
    if not 1<=args.samples<=10:parser.error('Choose 1–10 samples')
    run(args.identity,args.output,args.samples,args.scoped_cache,args.variant,args.baseline_ref)
