"""Package an already evaluated, explicitly approved adapter for source releases."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from agent.checkpoints import inventory
from agent.deployment import review


def build(candidate,candidate_report,baselines,output,approve=False,note=''):
    if not approve or not note.strip():raise ValueError('Explicit owner approval and a review note are required')
    candidate=Path(candidate).expanduser().resolve();output=Path(output).expanduser().resolve()
    if output==candidate or candidate in output.parents or output in candidate.parents:
        raise ValueError('Keep release output separate from original checkpoints')
    if output.exists():raise ValueError('Use a new model release directory')
    with tempfile.TemporaryDirectory() as folder:
        decision=review(candidate,candidate_report,baselines,Path(folder)/'review.json')
    if not decision['numeric_gate_passed']:raise ValueError('Failed candidates cannot become approved release bundles')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zenith-bundle-',dir=output.parent) as folder:
        root=Path(folder)/'bundle';root.mkdir()
        shutil.copytree(candidate,root/'checkpoint')
        evidence=root/'evaluation';evidence.mkdir()
        shutil.copyfile(candidate_report,evidence/'candidate.json')
        names=[]
        for i,baseline in enumerate(baselines):
            name=f'evaluation/baseline-{i:02d}.json';shutil.copyfile(baseline,root/name);names.append(name)
        card=f'''# Zenith continued-training release

This adapter continues the existing Zenith trained checkpoint on the original
{decision['base_model']} base at revision
{decision['base_revision']}. It is not a new foundation model.
The base architecture and tokenizer are preserved. Zenith-authored training data
and adapter licensing use Apache-2.0; upstream model terms also apply. Upstream
identifiers and generated PEFT metadata are retained. Base weights are separate.

The evaluation directory records raw answers, settings, file hashes, and all
comparison baselines. The small public diagnostic suite is a development check,
not a standardized measure of expert competence. Review the project model card
and independent transfer evidence for limitations. Training reports record their
original unpromoted state; deployment receipts record subsequent activation.

Activate with `zenith deployment use-release --bundle PATH_TO_THIS_FOLDER --approve`.
The original base must be cached. Activation verifies the bundle, recomputes
quality gates, tests model loading, backs up the profile, and preserves rollback.
Restricted security tools stay disabled.
'''
        (root/'README.md').write_text(card,encoding='utf-8',newline='\n')
        release={'schema_version':1,'id':output.name,'checkpoint':'checkpoint',
            'candidate_report':'evaluation/candidate.json','baseline_reports':names,
            'approved_for_local_activation':True,'approval_note':note,
            'diagnostic_passed':decision['diagnostic_passed'],'diagnostic_cases':decision['diagnostic_cases'],
            'files':inventory(root),'base_weights_bundled':False,'automatic_promotion':False,
            'license':'Apache-2.0','limitations':decision['limitations']}
        (root/'release.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8',newline='\n')
        if inventory(root/'checkpoint')!=decision['checkpoint_files']:raise ValueError('Checkpoint changed during packaging')
        root.rename(output)
    return release


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--candidate-report',type=Path,required=True)
    parser.add_argument('--baseline-report',type=Path,action='append',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--approve',action='store_true');parser.add_argument('--review-note',required=True)
    args=parser.parse_args();print(json.dumps(build(args.candidate,args.candidate_report,args.baseline_report,args.output,args.approve,args.review_note),indent=2))


if __name__=='__main__':main()
