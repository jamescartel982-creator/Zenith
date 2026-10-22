"""One resumable-artifact directory per bounded, unpromoted training experiment."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from agent.curriculum import prepare,RESOURCE_ROOT
from agent.paths import zenith_home


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=RESOURCE_ROOT/'starter-v1.jsonl')
    parser.add_argument('--output',type=Path,required=True,help='New run directory; existing experiment artifacts are preserved')
    parser.add_argument('--max-steps',type=int,default=40)
    parser.add_argument('--skip-generation-benchmark',action='store_true',help='Record that answer-quality gates remain untested')
    args=parser.parse_args()
    if not 1<=args.max_steps<=5000:parser.error('--max-steps must be 1–5000')
    root=args.output.expanduser().resolve()
    if root.exists() and any(root.iterdir()):parser.error('Use a new output directory to keep runs immutable')
    root.mkdir(parents=True,exist_ok=True)
    dataset=root/'dataset';manifest=prepare(args.input,dataset,balance_topics=True)
    adapter=root/'adapter';logs=root/'logs';logs.mkdir()
    model='Qwen/Qwen2.5-0.5B-Instruct';revision='7ae557604adf67be50417f59c2c2f167def9a775'
    base_env={**os.environ,'AI_PROVIDER':'huggingface','HF_MODEL':model,'HF_REVISION':revision,
        'ZENITH_CPU_THREADS':'2','OMP_NUM_THREADS':'2','ZENITH_CALIBRATION_FILE':'','ZENITH_ADAPTER':'',
        'TEMPERATURE':'0','CONTEXT_TOKENS':'2048','ZENITH_RESPONSE_MODE':'fast'}
    def run(name,module,arguments,environment=None,allow_gate_failure=False):
        command=[sys.executable,'-m',module,*map(str,arguments)]
        print('Running '+name,flush=True)
        with (logs/(name+'.stdout')).open('w',encoding='utf-8') as stdout,(logs/(name+'.stderr')).open('w',encoding='utf-8') as stderr:
            result=subprocess.run(command,env=environment or base_env,stdout=stdout,stderr=stderr)
        if result.returncode and not allow_gate_failure:raise RuntimeError(name+' failed; inspect its saved logs')
        return result.returncode
    try:
        run('train','scripts.train_lora',['--base-model',model,'--revision',revision,'--train-data',dataset/'train.jsonl',
            '--eval-data',dataset/'validation.jsonl','--dataset-manifest',dataset/'manifest.json','--output-dir',adapter,
            '--max-length','256','--max-steps',args.max_steps,'--gradient-accumulation','1','--learning-rate','0.0001','--cpu-threads','2'])
        for name,extra in [('baseline-test',[]),('candidate-test',['--adapter',adapter])]:
            run(name,'scripts.evaluate',['--base-model',model,'--revision',revision,'--data',dataset/'test.jsonl','--max-length','256',*extra])
            value=json.loads((logs/(name+'.stdout')).read_text(encoding='utf-8'))
            (root/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        comparison=None
        if not args.skip_generation_benchmark:
            run('baseline-benchmark','agent.quality',['--max-new-tokens','64','--output',root/'baseline-benchmark.json'])
            candidate_env={**base_env,'ZENITH_ADAPTER':str(adapter)}
            run('candidate-benchmark','agent.quality',['--max-new-tokens','64','--output',root/'candidate-benchmark.json','--baseline',root/'baseline-benchmark.json'],candidate_env,True)
            comparison=json.loads((root/'candidate-benchmark.json').read_text(encoding='utf-8'))['comparison']
        before=json.loads((root/'baseline-test.json').read_text(encoding='utf-8'))['mean_target_loss']
        after=json.loads((root/'candidate-test.json').read_text(encoding='utf-8'))['mean_target_loss']
        report={'dataset':manifest,'base_model':model,'revision':revision,'max_steps':args.max_steps,
            'final_test_loss_before':before,'final_test_loss_after':after,'generation_comparison':comparison,
            'passed_numeric_gates':after<=before and comparison is not None and comparison['quality_gate_passed'],
            'automatic_promotion':False,'promoted':False,
            'limitations':['A small authored starter curriculum is not comprehensive subject training.','Loss improvements do not establish general capability improvement.','Inspect held-out answers and representative domain tests before adoption.']}
        (root/'campaign_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    except (RuntimeError,OSError,ValueError) as exc:parser.error(str(exc))
    print('Saved immutable run artifacts at '+str(root))
    print('Candidate remains unpromoted. Review numeric gates, answer quality, data rights and intended use.')


if __name__=='__main__':main()
