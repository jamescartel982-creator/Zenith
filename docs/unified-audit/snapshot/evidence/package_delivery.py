from pathlib import Path
import shutil,json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';OUT=ROOT/'review-package'
assert not OUT.exists();OUT.mkdir();(OUT/'evidence').mkdir();(OUT/'reports').mkdir()
shutil.copy2(ROOT/'README.md',OUT/'README.md')
for path in (ROOT/'reports').iterdir():
 if path.is_file():shutil.copy2(path,OUT/'reports'/path.name)
for path in E.iterdir():
 if not path.is_file() or '.private.' in path.name:continue
 if path.suffix in ('.json','.py','.log','.txt','.md','.gz') or path.name.endswith('.stderr'):shutil.copy2(path,OUT/'evidence'/path.name)
assert not any('.private.' in str(p) for p in OUT.rglob('*'))
assert not any(p.suffix in ('.db','.sqlite','.sqlite3','.safetensors','.bin','.env') for p in OUT.rglob('*'))
manifest=[]
for path in sorted(OUT.rglob('*')):
 if path.is_file():manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(OUT)))
(OUT/'SHA256SUMS').write_text('\n'.join(manifest)+'\n')
archive=ROOT/'zenith-unified-audit.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for path in sorted(OUT.rglob('*')):
  if path.is_file():z.write(path,str(path.relative_to(OUT)))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for line in z.read('SHA256SUMS').decode().splitlines():
  digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'members':len(manifest)+1,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'private_receipts_excluded':True,'integrity_passed':True},indent=2))
