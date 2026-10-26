from pathlib import Path
import json,hashlib,subprocess,csv,shutil
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';R=ROOT/'reports'
roots={'openclaw':Path('/workspace/openclaw-review-20261025/openclaw'),'hermes':ROOT/'hermes-agent','zenith-main':ROOT/'zenith-main','zenith-pr19':Path('/workspace/zenith-platform'),'zenith-pr18':Path('/workspace/Zenith')}
commits={}
for name,path in roots.items():
 sha=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
 dirty=subprocess.check_output(['git','-C',str(path),'status','--porcelain','--untracked-files=all'],text=True).strip()
 assert not dirty,(name,dirty)
 commits[name]={'commit':sha,'source_worktree_clean':True}
before=json.loads((E/'protected-before.private.json').read_text());after=json.loads((E/'protected-after.private.json').read_text())
assert all(before[k]==after[k] for k in ('model','revision','adapter_files','profile_sha256'))
public={'audit_only':True,'repositories':commits,'profile_unchanged':True,'selected_model_identity_unchanged':True,'selected_adapter_files_unchanged':True,'model':after['model'],'revision':after['revision'],'selected_adapter_sha256':after['adapter_files'].get('adapter_model.safetensors'),'selected_adapter_tokenizer_file_sha256':after['adapter_files'].get('tokenizer.json'),'private_receipts_excluded':True}
(E/'protection-verification.json').write_text(json.dumps(public,indent=2)+'\n')
shutil.copy2('/workspace/openclaw-review-20261025/evidence/zenith-model-verification.json',E/'zenith-model-verification.prior.json')
shutil.copy2('/workspace/zenith-platform/docs/platform/native-smoke.json',E/'pr19-native-smoke.prior.json')
for name,path in roots.items():
 if name in ('openclaw','hermes','zenith-main'):
  shutil.copy2(path/'LICENSE',E/(name+'-LICENSE.txt'))
  if (path/'THIRD_PARTY_NOTICES.md').is_file():shutil.copy2(path/'THIRD_PARTY_NOTICES.md',E/(name+'-THIRD_PARTY_NOTICES.md'))
rows=json.loads((E/'master-feature-matrix.json').read_text())
for row in rows:
 paths=[s['path'] for s in row['sources']]
 if row['entry_type']=='catalog_reference': a='BLOCKED: external package source/license/access review required'
 elif row['entry_type']=='documentation_surface':a='COVERAGE ONLY: documentation surface; reconcile with source behavior before parity acceptance'
 elif any(any(v in '/'+p.lower()+'/' for v in ('/test/','/tests/','/qa/','/fixtures/','/vendor/')) for p in paths):a='REVIEW: fixture/QA/vendor path; not assumed to be a deployable integration'
 else:a='PROPOSED APPLICABLE: confirm configuration, platform and legal access before implementation'
 row['applicability_review']=a
(E/'master-feature-matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
with (R/'MASTER_FEATURE_PARITY_MATRIX.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in rows for k in x)));writer.writeheader()
 for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
print('Protection verified for five clean source views; matrix applicability labels added.')
