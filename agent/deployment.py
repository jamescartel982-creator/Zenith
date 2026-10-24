"""Explicit local promotion with verified evidence, profile backup, and rollback.

This is a trusted operating-system administrator command, never a chat tool.
It does not publish weights or grant cybersecurity execution capabilities.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4
from .checkpoints import digest, inventory
from .expansion_eval import compare, validate_report
from .paths import config_file, zenith_home


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(value,handle,indent=2);handle.write('\n')


def review(candidate,candidate_report,baseline_reports,output):
    candidate=Path(candidate).expanduser().resolve()
    destination=Path(output).expanduser().resolve()
    if destination==candidate or candidate in destination.parents:
        raise ValueError('Keep review outputs outside the original checkpoint')
    measured=validate_report(read_json(candidate_report))
    if measured.get('production_base_only') is not False:
        raise ValueError('Candidate evaluation must include its trained adapter')
    files=inventory(candidate)
    if measured.get('checkpoint_files')!=files:
        raise ValueError('Candidate changed since evaluation')
    from .checkpoints import parent_metadata
    _,_,training=parent_metadata(candidate)
    for field in ['base_model','base_revision','tokenizer_sha256']:
        if training.get(field)!=measured[field]:raise ValueError('Training/evaluation identity differs: '+field)
    baselines=[validate_report(read_json(path)) for path in baseline_reports]
    if len(baselines)<2 or not any(b.get('production_base_only') is True for b in baselines) or not any(b.get('production_base_only') is False for b in baselines):
        raise ValueError('Provide both production and trained-parent baselines')
    parent=training.get('parent_files')
    if not any(b.get('production_base_only') is False and b.get('checkpoint_files')==parent for b in baselines):
        raise ValueError('Missing immediate trained-parent evaluation')
    comparisons=[compare(b,measured,b) for b in baselines]
    result={'schema_version':1,'candidate':str(candidate),'checkpoint_files':files,
        'base_model':measured['base_model'],'base_revision':measured['base_revision'],
        'tokenizer_sha256':measured['tokenizer_sha256'],
        'candidate_report':{'path':str(Path(candidate_report).resolve()),'sha256':digest(candidate_report)},
        'baseline_reports':[{'path':str(Path(p).resolve()),'sha256':digest(p)} for p in baseline_reports],
        'comparisons':comparisons,'numeric_gate_passed':all(c['numeric_gate_passed'] for c in comparisons),
        'diagnostic_passed':sum(r['passed'] for r in measured['results']),
        'diagnostic_cases':len(measured['results']),'human_review_required':True,
        'deployment_approved':False,'automatic_promotion':False,
        'limitations':['Development diagnostics are not a sealed expert benchmark.','Review raw answers and independent held-out results before explicitly approving activation.']}
    write_new(output,result)
    return result


def checked_review(path):
    saved=read_json(path)
    evidence=[saved['candidate_report'],*saved['baseline_reports']]
    if any(digest(row['path'])!=row['sha256'] for row in evidence):raise ValueError('Review evidence changed')
    # Rebuild the decision from raw answers; a hand-edited passed flag is insufficient.
    with tempfile.TemporaryDirectory() as folder:
        fresh=review(saved['candidate'],saved['candidate_report']['path'],[r['path'] for r in saved['baseline_reports']],Path(folder)/'review.json')
    if not fresh['numeric_gate_passed']:raise ValueError('Candidate still fails regression gates; activation denied')
    return fresh


def profile_bytes(path):
    path=Path(path)
    return path.read_bytes() if path.exists() else None


def bytes_digest(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def replace_profile(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.zenith-profile-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def validate_activation(settings):
    """Refuse changed or rolled-back approved weights before model loading."""
    receipt_path=Path(settings.checkpoint_receipt).expanduser().resolve()
    receipt=read_json(receipt_path)
    if receipt.get('approved') is not True or (receipt_path.parent/'rollback.json').exists():
        raise ValueError('Checkpoint activation is absent or rolled back')
    if Path(settings.adapter).expanduser().resolve()!=Path(receipt['candidate']).resolve():
        raise ValueError('Active adapter differs from the approved checkpoint')
    if settings.model!=receipt['base_model'] or settings.revision!=receipt['base_revision']:
        raise ValueError('Active base identity differs from the approved checkpoint')
    if inventory(settings.adapter)!=receipt['checkpoint_files']:
        raise ValueError('Approved checkpoint files changed; refusing model loading')
    return receipt


def activate(review_path,profile=None,state_dir=None,approve=False,review_note=''):
    if not approve or not isinstance(review_note,str) or not review_note.strip() or len(review_note)>2000:
        raise ValueError('Explicit --approve and a human --review-note are required')
    reviewed=checked_review(review_path)
    # Real model/tokenizer load and inference, not only a manifest check.
    from .checkpoints import inspect_checkpoint
    inspection=inspect_checkpoint(reviewed['candidate'])
    import gc;gc.collect()
    if inspection['parent_files']!=reviewed['checkpoint_files'] or inspection['tokenizer_sha256']!=reviewed['tokenizer_sha256']:
        raise ValueError('Checkpoint identity changed while loading')
    profile=Path(profile or config_file()).expanduser().resolve()
    before=profile_bytes(profile)
    state=Path(state_dir or zenith_home()/'deployments').resolve()
    checkpoint=Path(reviewed['candidate']).resolve()
    if profile==checkpoint or checkpoint in profile.parents or state==checkpoint or checkpoint in state.parents:
        raise ValueError('Keep profiles and deployment records outside original checkpoints')
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:8]
    run=state/identifier
    # dotenv edits occur in a temporary copy, preserving unrelated settings.
    from dotenv import set_key
    with tempfile.TemporaryDirectory() as folder:
        target=Path(folder)/'config.env';target.write_bytes(before or b'')
        values={'AI_PROVIDER':'huggingface','HF_MODEL':reviewed['base_model'],
            'HF_REVISION':reviewed['base_revision'],'ZENITH_ADAPTER':reviewed['candidate'],
            'ZENITH_CHECKPOINT_RECEIPT':str(run/'receipt.json')}
        for key,value in values.items():set_key(str(target),key,value,quote_mode='always')
        after=target.read_bytes()
    run.mkdir(parents=True,exist_ok=False)
    try:run.chmod(0o700)
    except OSError:pass
    if before is not None:replace_profile(run/'previous-config.env',before)
    receipt={'schema_version':1,'id':identifier,'profile':str(profile),'profile_previously_existed':before is not None,
        'previous_profile_sha256':bytes_digest(before),'active_profile_sha256':bytes_digest(after),
        'candidate':reviewed['candidate'],'checkpoint_files':reviewed['checkpoint_files'],
        'base_model':reviewed['base_model'],'base_revision':reviewed['base_revision'],
        'tokenizer_sha256':reviewed['tokenizer_sha256'],
        'review_sha256':digest(review_path),'review_note':review_note.strip(),
        'approved':True,'inference_smoke_answer':inspection['inference'],
        'requires_restart':True,'network_tools_enabled':False,'published':False,
        'override_notice':'Explicit environment variables and checkout .env override the saved user profile.'}
    write_new(run/'receipt.json',receipt)
    if profile_bytes(profile)!=before:raise ValueError('Profile changed concurrently; activation cancelled')
    if inventory(reviewed['candidate'])!=reviewed['checkpoint_files']:
        raise ValueError('Checkpoint changed during activation; profile was preserved')
    replace_profile(profile,after)
    # A pointer is informational; immutable receipts carry the actual rollback evidence.
    replace_profile(state/'active.json',(json.dumps({'id':identifier,'receipt':str(run/'receipt.json')})+'\n').encode())
    return receipt


def rollback(receipt_path):
    receipt_path=Path(receipt_path).resolve();receipt=read_json(receipt_path)
    if (receipt_path.parent/'rollback.json').exists():raise ValueError('This deployment was already rolled back')
    profile=Path(receipt['profile'])
    if bytes_digest(profile_bytes(profile))!=receipt['active_profile_sha256']:
        raise ValueError('Profile changed since activation; inspect it before rollback')
    if receipt['profile_previously_existed']:
        backup=receipt_path.parent/'previous-config.env'
        if digest(backup)!=receipt['previous_profile_sha256']:raise ValueError('Rollback backup changed')
        replace_profile(profile,backup.read_bytes())
    else:profile.unlink()
    result={'rolled_back':True,'deployment':receipt['id'],'requires_restart':True}
    write_new(receipt_path.parent/'rollback.json',result)
    active=receipt_path.parent.parent/'active.json'
    if active.exists() and read_json(active).get('id')==receipt['id']:active.unlink()
    return result


def use_release(bundle,approve=False,profile=None,state_dir=None,cache_dir=None,review_note='',download_base=False):
    """Copy an approved source-release bundle to stable user storage, then review."""
    if not approve:raise ValueError('Explicit --approve is required to activate a model release')
    bundle=Path(bundle).expanduser().resolve();release=read_json(bundle/'release.json')
    if release.get('schema_version')!=1 or release.get('approved_for_local_activation') is not True:
        raise ValueError('This release is not approved for local activation')
    observed=inventory(bundle);observed.pop('release.json',None)
    if observed!=release.get('files'):raise ValueError('Release bundle files changed')
    from .integrity import safe_source_path
    def located(root,key):return safe_source_path(root,release[key])
    source_candidate=located(bundle,'checkpoint')
    if not (source_candidate/'adapter_model.safetensors').is_file():raise ValueError('Release is missing the complete adapter file')
    cache=Path(cache_dir or zenith_home()/'model_releases').resolve()
    if cache==bundle or bundle in cache.parents or cache in bundle.parents:
        raise ValueError('Keep the release cache separate from the source bundle')
    stable=cache/digest(bundle/'release.json')
    cache.mkdir(parents=True,exist_ok=True)
    if stable.exists():
        if inventory(stable)!=inventory(bundle):raise ValueError('Cached release changed; refusing to overwrite it')
    else:
        with tempfile.TemporaryDirectory(prefix='.zenith-release-',dir=cache) as folder:
            temporary=Path(folder)/'bundle';shutil.copytree(bundle,temporary)
            if inventory(temporary)!=inventory(bundle):raise ValueError('Release changed during copy')
            os.rename(temporary,stable)
    candidate=located(stable,'checkpoint')
    candidate_report=located(stable,'candidate_report')
    baselines=[safe_source_path(stable,value) for value in release['baseline_reports']]
    review_path=cache/('review-'+uuid4().hex+'.json')
    result=review(candidate,candidate_report,baselines,review_path)
    if not result['numeric_gate_passed']:raise ValueError('Published bundle still fails the current regression gate')
    if download_base:
        from .models import download
        download({'provider':'huggingface','model':result['base_model'],'revision':result['base_revision']},
            offline=os.getenv('HF_HUB_OFFLINE','').lower() in {'1','true','yes'})
    return activate(review_path,profile,state_dir,approve,review_note or 'Operator selected the approved source-release bundle '+str(release.get('id','')))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('review');p.add_argument('--candidate',type=Path,required=True);p.add_argument('--candidate-report',type=Path,required=True)
    p.add_argument('--baseline-report',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('activate');p.add_argument('--review',type=Path,required=True);p.add_argument('--profile',type=Path);p.add_argument('--state-dir',type=Path)
    p.add_argument('--approve',action='store_true');p.add_argument('--review-note',required=True)
    p=sub.add_parser('rollback');p.add_argument('--receipt',type=Path,required=True)
    p=sub.add_parser('status');p.add_argument('--state-dir',type=Path)
    p=sub.add_parser('use-release');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--approve',action='store_true')
    p.add_argument('--profile',type=Path);p.add_argument('--state-dir',type=Path);p.add_argument('--cache-dir',type=Path);p.add_argument('--review-note',default='')
    p.add_argument('--download-base',action='store_true',help='Cache only the verified release base, respecting offline mode')
    args=parser.parse_args()
    try:
        if args.action=='review':result=review(args.candidate,args.candidate_report,args.baseline_report,args.output)
        elif args.action=='activate':result=activate(args.review,args.profile,args.state_dir,args.approve,args.review_note)
        elif args.action=='rollback':result=rollback(args.receipt)
        elif args.action=='use-release':result=use_release(args.bundle,args.approve,args.profile,args.state_dir,args.cache_dir,args.review_note,args.download_base)
        else:
            active=Path(args.state_dir or zenith_home()/'deployments')/'active.json'
            result=read_json(active) if active.is_file() else {'active_deployment':None}
    except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))
    return 1 if args.action=='review' and not result['numeric_gate_passed'] else 0


if __name__=='__main__':raise SystemExit(main())
