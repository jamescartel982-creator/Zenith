"""Reproducible diagnostic evaluations, latency comparisons and empirical calibration."""
import argparse
from collections import defaultdict
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import statistics
import tempfile
import time
from uuid import uuid4
from .config import Settings
from .paths import zenith_home
from . import __version__

DEFAULT_SUITE=Path(__file__).parent/'evaluation'/'suite-v1.json'
ABSTENTION=re.compile(r"(?:don.t know|do not know|don.t have|do not have|cannot (?:know|determine|provide|guarantee)|can.t (?:know|determine|provide|guarantee)|not (?:known|available|documented)|unknown|no way to|not possible|no reliable)",re.I)


def configuration_signature(settings,mode=None,reply_style=None):
    fields={'version':__version__,'provider':settings.provider,'model':settings.model_name,'revision':settings.revision,
            'adapter':settings.adapter,'max_new_tokens':settings.max_new_tokens,'context_tokens':settings.context_tokens,
            'temperature':settings.temperature,'mode':mode or settings.response_mode,'team_sha256':None,
            'reply_style':reply_style or settings.reply_style,'fast_max_new_tokens':settings.fast_max_new_tokens,'fast_history_turns':settings.fast_history_turns}
    fields.update(device=settings.device,cpu_threads=settings.cpu_threads)
    if settings.provider in {'orchestrated', 'reasoning'}:
        import os
        fields.update(orchestration_mode=settings.orchestration_mode, reasoning_effort=settings.reasoning_effort,
                      native_model=settings.model, native_adapter=settings.adapter, ollama_model=settings.ollama_model,
                      local_server_model=settings.local_server_model, tiny_checkpoint=settings.tiny_checkpoint,
                      allow_external=settings.allow_external, native_provider=os.getenv('ZENITH_NATIVE_PROVIDER','huggingface'),
                      external_models_sha256=hashlib.sha256(os.getenv('ZENITH_EXTERNAL_MODELS','[]').encode()).hexdigest())
    if settings.team_config:
        fields['team_sha256']=hashlib.sha256(Path(settings.team_config).read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()


def percentile(values,p):
    if not values:return None
    values=sorted(values);x=(len(values)-1)*p;left=int(x);right=min(left+1,len(values)-1)
    return values[left]+(values[right]-values[left])*(x-left)


def score_case(case,answer):
    normalized=' '.join(answer.casefold().split())
    def contains(text):return bool(re.search(r'(?<!\w)'+re.escape(text.casefold())+r'(?!\w)',normalized))
    abstained=bool(ABSTENTION.search(answer))
    if case['scorer']=='abstain':correct=abstained
    elif case['scorer']=='contains':correct=all(contains(v) for v in case['expected'])
    elif case['scorer']=='contains-any':correct=any(contains(v) for v in case['expected'])
    elif case['scorer']=='exact':correct=normalized in [' '.join(v.casefold().split()) for v in case['expected']]
    else:raise ValueError('Unknown task scorer')
    from .admin import contains_admin_code
    if contains_admin_code(answer):correct=False
    return {'passed':bool(correct),'abstained':abstained,'scorer':case['scorer']}


def summarize(results):
    groups=defaultdict(list)
    for row in results:
        groups['all'].append(row)
        for label in row['slices']:groups[label].append(row)
    summary={}
    for label,rows in groups.items():
        answered=[r for r in rows if not r['abstained']]
        abstain_cases=[r for r in rows if r['should_abstain']]
        expected_answer=[r for r in rows if not r['should_abstain']]
        summary[label]={'cases':len(rows),'accuracy':sum(r['passed'] for r in rows)/len(rows),
            'coverage':len(answered)/len(rows),'answered_error_rate':sum(not r['passed'] for r in answered)/len(answered) if answered else None,
            'abstention_recall':sum(r['abstained'] for r in abstain_cases)/len(abstain_cases) if abstain_cases else None,
            'unnecessary_abstention_rate':sum(r['abstained'] for r in expected_answer)/len(expected_answer) if expected_answer else None,
            'latency_p50_ms':percentile([r['latency_ms'] for r in rows],0.5),'latency_p95_ms':percentile([r['latency_ms'] for r in rows],0.95)}
        first=[r['first_text_ms'] for r in rows if r.get('first_text_ms') is not None]
        summary[label]['first_visible_text_p50_ms']=percentile(first,0.5)
        summary[label]['first_visible_text_p95_ms']=percentile(first,0.95)
    return summary


def run_suite(settings,suite_path=DEFAULT_SUITE,mode='fast',repeat=1,purpose='diagnostic'):
    from .core import Agent
    path=Path(suite_path);suite=json.loads(path.read_text(encoding='utf-8'))
    if not 1<=repeat<=20:raise ValueError('repeat must be 1–20')
    results=[]
    with tempfile.TemporaryDirectory(prefix='zenith-evaluation-') as directory:
        agent=Agent(replace(settings,data_dir=directory,response_mode=mode))
        started=time.perf_counter()
        # Separate cold start from the measured requests. May load model weights.
        agent.provider.generate([{'role':'system','content':'You are Zenith.'},{'role':'user','content':'Say hello briefly.'}])
        cold_ms=(time.perf_counter()-started)*1000
        for iteration in range(repeat):
            for case in suite['cases']:
                started=time.perf_counter()
                result=agent.answer(case['prompt'],str(uuid4()),response_mode=mode)
                row={'id':case['id'],'iteration':iteration,'prompt':case['prompt'],'response':result['response'],
                     'latency_ms':(time.perf_counter()-started)*1000,'slices':case['slices']+['path:'+result['quality']['method']],
                     'should_abstain':case['should_abstain'],'quality':result['quality'],
                     'first_text_ms':result.get('time_to_first_text_ms'),'performance':result.get('performance')}
                row.update(score_case(case,row['response']));results.append(row)
    return {'schema_version':1,'purpose':purpose,'suite_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'model':settings.model_name,'revision':settings.revision,'adapter':settings.adapter,'provider':settings.provider,
            'python':platform.python_version(),'cpu_threads':settings.cpu_threads,'max_new_tokens':settings.max_new_tokens,
            'temperature':settings.temperature,'context_tokens':settings.context_tokens,
            'response_mode':mode,'reply_style':settings.reply_style,'cold_start_ms':cold_ms,'results':results,'slices':summarize(results),
            'configuration_sha256':configuration_signature(settings,mode),
            'calibration':{'available':False,'brier_score':None,'expected_calibration_error':None,'note':'No calibrated probabilities supplied; model self-confidence is not measured confidence.'},
            'limitations':['Rule-based answer scorers require human review for nuanced correctness.','Public diagnostic cases are not a sealed generalization benchmark.','Latency depends on hardware, load, output length and cache state.']}


def compare_reports(current,baseline,suite_path=DEFAULT_SUITE):
    suite=json.loads(Path(suite_path).read_text(encoding='utf-8'))
    if current['suite_sha256']!=baseline['suite_sha256']:raise ValueError('Comparison requires identical suite hashes')
    cases={row['id']:row for row in suite['cases']}
    baseline_rows=[]
    for row in baseline['results']:
        case=cases[row['id']]
        baseline_rows.append({**row,**score_case(case,row['response']),'should_abstain':case['should_abstain']})
    before=summarize(baseline_rows);after=current['slices']
    regressions=[label for label in before if label in after and after[label]['accuracy']+1e-9<before[label]['accuracy']]
    ratio=after['all']['latency_p50_ms']/before['all']['latency_p50_ms'] if before['all']['latency_p50_ms'] else None
    model_ids={row['id'] for row in current['results'] if row.get('quality',{}).get('method')=='model'}
    old_model=[row for row in baseline_rows if row['id'] in model_ids]
    new_model=[row for row in current['results'] if row['id'] in model_ids]
    model_comparison={'cases':len(new_model),'baseline_total_p50_ms':percentile([row['latency_ms'] for row in old_model],0.5),
        'candidate_total_p50_ms':percentile([row['latency_ms'] for row in new_model],0.5),
        'candidate_first_visible_text_p50_ms':percentile([row['first_text_ms'] for row in new_model if row.get('first_text_ms') is not None],0.5),
        'baseline_response_characters':sum(len(row['response']) for row in old_model),
        'candidate_response_characters':sum(len(row['response']) for row in new_model),
        'note':'Matched model-generated cases; deterministic fast paths are excluded. Output lengths and system instructions can differ.'}
    return {'baseline':before,'candidate':after,'accuracy_regression_slices':regressions,'latency_p50_ratio':ratio,
            'latency_goal_ratio':suite.get('targets',{}).get('fast_latency_ratio',0.7),
            'latency_goal_met':ratio is not None and ratio<=suite.get('targets',{}).get('fast_latency_ratio',0.7),
            'quality_gate_passed':not regressions,'automatic_promotion':False,'model_generated_cases':model_comparison}


def fit_calibration(report,min_cases=5):
    if report.get('purpose')!='calibration-validation':raise ValueError('Fit calibration only on a designated validation report, never a final test')
    groups=defaultdict(list)
    seen=set()
    for row in report['results']:
        if row['id'] in seen:continue
        seen.add(row['id']);groups[row.get('quality',{}).get('method','model')].append(bool(row['passed']))
    estimates={}
    for method,values in groups.items():
        if len(values)<min_cases:continue
        n=len(values);p=sum(values)/n;z=1.96;denominator=1+z*z/n
        center=(p+z*z/(2*n))/denominator;radius=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/denominator
        estimates[method]={'cases':n,'successes':sum(values),'estimate':(sum(values)+1)/(n+2),
                           'wilson_lower':max(0,center-radius),'wilson_upper':min(1,center+radius)}
    return {'schema_version':1,'kind':'empirical-method-groups','model':report['model'],'revision':report['revision'],
            'provider':report['provider'],'adapter':report.get('adapter',''),'validation_suite_sha256':report['suite_sha256'],
            'configuration_sha256':report.get('configuration_sha256'),
            'groups':estimates,'min_cases':min_cases,'warning':'Aggregate validation frequency, not an individual model probability. Distribution shift can invalidate it.'}


def apply_calibration(report,artifact):
    if not artifact.get('configuration_sha256') or report.get('configuration_sha256')!=artifact['configuration_sha256']:
        raise ValueError('Calibration does not match this exact model/runtime configuration')
    if report['suite_sha256']==artifact['validation_suite_sha256']:
        raise ValueError('Evaluate calibration on an independent suite, not the suite used to fit it')
    scored=[]
    for row in report['results']:
        group=artifact['groups'].get(row.get('quality',{}).get('method','model'))
        if group:
            probability=group['estimate'];scored.append((probability,int(row['passed'])))
            row['confidence']=probability;row['confidence_source']='validation-method-group'
    if not scored:raise ValueError('No validation-calibrated methods cover this report')
    bins=defaultdict(list)
    for probability,correct in scored:bins[min(9,int(probability*10))].append((probability,correct))
    ece=sum(len(rows)/len(scored)*abs(statistics.mean(p for p,_ in rows)-statistics.mean(y for _,y in rows)) for rows in bins.values())
    report['calibration']={'available':True,'coverage':len(scored)/len(report['results']),
        'brier_score':statistics.mean((p-y)**2 for p,y in scored),'expected_calibration_error':ece,
        'note':'Independent-suite check of aggregate method-group validation estimates; not an individual model confidence guarantee.'}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,default=DEFAULT_SUITE)
    parser.add_argument('--mode',choices=['fast','thorough'],default='fast')
    parser.add_argument('--repeat',type=int,default=1)
    parser.add_argument('--output',type=Path,default=zenith_home()/'evaluations'/'latest.json')
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--purpose',choices=['diagnostic','calibration-validation','final-test'],default='diagnostic')
    parser.add_argument('--fit-calibration',type=Path,help='Fit from this existing validation report instead of generating answers')
    parser.add_argument('--max-new-tokens',type=int,default=None)
    parser.add_argument('--reply-style',choices=['auto','brief','full'],default=None)
    parser.add_argument('--calibration',type=Path,help='Evaluate a fitted method-group artifact on an independent suite')
    args=parser.parse_args()
    try:
        if args.fit_calibration:report=fit_calibration(json.loads(args.fit_calibration.read_text(encoding='utf-8')))
        else:
            settings=Settings()
            if args.max_new_tokens is not None:settings=replace(settings,max_new_tokens=args.max_new_tokens)
            if args.reply_style is not None:settings=replace(settings,reply_style=args.reply_style)
            report=run_suite(settings,args.suite,args.mode,args.repeat,args.purpose)
            if args.calibration:report=apply_calibration(report,json.loads(args.calibration.read_text(encoding='utf-8')))
            if args.baseline:report['comparison']=compare_reports(report,json.loads(args.baseline.read_text(encoding='utf-8')),args.suite)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    print(json.dumps({'saved':str(args.output),'slices':report.get('slices'),'comparison':report.get('comparison'),'kind':report.get('kind')},indent=2))
    return int(bool(report.get('comparison',{}).get('accuracy_regression_slices')))


if __name__=='__main__':raise SystemExit(main())
