"""Rerun approved source-release diagnostics and reject new regressions."""
import argparse
import json
from pathlib import Path
from agent.checkpoints import inventory
from agent.integrity import safe_source_path
from agent.expansion_eval import evaluate,compare


def check(bundle,output):
    bundle=Path(bundle).resolve();release=json.loads((bundle/'release.json').read_text(encoding='utf-8'))
    observed=inventory(bundle);observed.pop('release.json',None)
    if release.get('approved_for_local_activation') is not True or observed!=release.get('files'):
        raise ValueError('Unapproved or modified model release')
    candidate=safe_source_path(bundle,release['checkpoint'])
    approved=json.loads(safe_source_path(bundle,release['candidate_report']).read_text(encoding='utf-8'))
    measured=evaluate(candidate,output,max_new_tokens=approved['max_new_tokens'],system_prompt=approved.get('system_prompt'))
    paths=[release['candidate_report'],*release['baseline_reports']]
    comparisons=[]
    for path in paths:
        baseline=json.loads(safe_source_path(bundle,path).read_text(encoding='utf-8'))
        comparisons.append({'baseline':path,**compare(baseline,measured,baseline)})
    result={'numeric_gate_passed':all(r['numeric_gate_passed'] for r in comparisons),
        'comparisons':comparisons,'production_profile_changed':False,'automatic_promotion':False}
    Path(str(output)+'.comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=check(args.bundle,args.output);print(json.dumps(result,indent=2))
    return 0 if result['numeric_gate_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
