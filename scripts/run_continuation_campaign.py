"""Checkpoint -> training -> comparison -> review bundle; no deployment action."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from agent.checkpoints import inventory


def run(parent,dataset,output,steps=80):
    root=Path(output).expanduser().resolve()
    parent=Path(parent).expanduser().resolve()
    dataset=Path(dataset).expanduser().resolve()
    if parent==root or parent in root.parents or root in parent.parents or dataset in root.parents:
        raise ValueError('Keep campaign artifacts separate from original checkpoints and versioned datasets')
    if root.exists():raise ValueError('Campaign requires a new experiment directory')
    root.mkdir(parents=True)
    logs=root/'logs';logs.mkdir()
    def command(name,module,args):
        with (logs/(name+'.log')).open('w',encoding='utf-8') as handle:
            subprocess.run([sys.executable,'-m',module,*map(str,args)],stdout=handle,stderr=subprocess.STDOUT,check=True)
    command('inspect','agent.checkpoints',['--parent',parent,'--output',root/'parent-inspection.json'])
    command('parent-benchmark','agent.expansion_eval',['--parent',parent,'--output',root/'parent-benchmark.json'])
    command('production-benchmark','agent.expansion_eval',['--parent',parent,'--production-base-only','--output',root/'production-benchmark.json'])
    command('train','agent.continual',['--parent',parent,'--dataset',dataset,'--output',root/'candidate','--steps',steps])
    command('candidate-benchmark','agent.expansion_eval',['--parent',root/'candidate','--output',root/'candidate-benchmark.json'])
    from agent.expansion_eval import compare
    read=lambda name:json.loads((root/name).read_text())
    comparison=compare(read('parent-benchmark.json'),read('candidate-benchmark.json'),read('production-benchmark.json'))
    report={'comparison':comparison,'candidate_files':inventory(root/'candidate'),'production_changed':False,
            'publication_approved':False,'automatic_promotion':False,
            'rollback':{'unchanged_parent':str(parent),'action':'Retain existing runtime settings. No deployment or model-profile update is performed.'}}
    (root/'review.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=80)
    args=parser.parse_args()
    try:result=run(args.parent,args.dataset,args.output,args.steps)
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))
    return 0 if result['comparison']['numeric_gate_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
