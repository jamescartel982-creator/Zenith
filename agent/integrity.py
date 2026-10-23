"""Offline consistency checks for source releases and installed wheel files."""
import argparse
import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path,PurePosixPath
import re
import site
import sys
from . import __version__

MANIFEST_NAME='release-manifest.json'


def file_digest(path,algorithm='sha256'):
    digest=hashlib.new(algorithm)
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.digest()


def safe_source_path(root,name):
    if not isinstance(name,str) or not name or len(name)>1024 or '\\' in name or ':' in name:
        raise ValueError('Invalid source path')
    pure=PurePosixPath(name)
    if pure.is_absolute() or '..' in pure.parts:raise ValueError('Unsafe source path')
    target=(root/Path(*pure.parts)).resolve()
    if root not in target.parents:raise ValueError('Source path leaves the release directory')
    return target


def source_fingerprint(path,normalization='raw'):
    if normalization=='raw':return path.stat().st_size,file_digest(path).hex()
    if normalization!='lf' or path.stat().st_size>64*1024**2:raise ValueError('Unsupported text normalization or oversized text file')
    data=path.read_bytes().replace(b'\r\n',b'\n')
    return len(data),hashlib.sha256(data).hexdigest()


def report(scope,checked,errors,**extra):
    return {'schema_version':1,'version':__version__,'scope':scope,'ok':not errors,'checked_files':checked,
            'errors':errors[:30],'error_count':len(errors),
            'note':'Consistency check, not a signature or proof of publisher authenticity. Model weights and local private data are separate.',**extra}


def verify_source(directory):
    root=Path(directory).expanduser().resolve();errors=[];checked=0
    path=root/MANIFEST_NAME
    try:
        if path.stat().st_size>2*1024**2:raise ValueError('Oversized release manifest')
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version')!=1 or not isinstance(data.get('files'),list) or not 1<=len(data['files'])<=20000:
            raise ValueError('Invalid release manifest schema')
        if data.get('version')!=__version__:errors.append('Source manifest version differs from the running Zenith code')
        seen=set()
        for row in data['files']:
            name=row['path'];target=safe_source_path(root,name)
            if name in seen or name==MANIFEST_NAME:raise ValueError('Duplicate or self-referential source entry')
            seen.add(name)
            if not re.fullmatch(r'[0-9a-f]{64}',row['sha256']) or type(row['size']) is not int or row['size']<0:
                raise ValueError('Invalid checksum or file size')
            if not target.is_file():errors.append('Missing: '+name);continue
            checked+=1
            size,digest=source_fingerprint(target,row.get('normalization','raw'))
            if size!=row['size'] or digest!=row['sha256']:errors.append('Modified: '+name)
        required={'agent/__init__.py','README.md','LICENSE','pyproject.toml','install.py','install.sh','install.ps1','run.sh','run.ps1'}
        for name in sorted(required-seen):errors.append('Required release entry omitted: '+name)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors.append('Cannot verify source manifest: '+type(exc).__name__)
    return report('source',checked,errors,manifest=MANIFEST_NAME)


def verify_installed(distribution=None):
    errors=[];checked=0;unhashed=0
    try:
        dist=distribution or importlib.metadata.distribution('zenith-local')
        direct=json.loads(dist.read_text('direct_url.json') or '{}')
        if direct.get('dir_info',{}).get('editable'):
            return report('installed-wheel',0,['Editable installations do not inventory source files. Use zenith verify --source PATH_TO_CHECKOUT.'])
        if dist.version!=__version__:errors.append('Installed metadata and running code have different versions; reinstall Zenith')
        package=Path(dist.locate_file('agent/__init__.py')).resolve()
        if package!=Path(__file__).resolve().with_name('__init__.py'):
            errors.append('Running code is outside the installed wheel; run from another directory or verify the source checkout')
        files=dist.files
        if not files:raise ValueError('No installed file inventory')
        allowed=[Path(sys.prefix).resolve(),Path(site.getuserbase()).resolve(),Path(dist.locate_file('')).resolve()]
        for item in files:
            target=Path(dist.locate_file(item)).resolve()
            if not any(base==target or base in target.parents for base in allowed):
                errors.append('Installed entry leaves its installation roots: '+str(item));continue
            if not target.is_file():errors.append('Missing: '+str(item));continue
            if not item.hash:
                unhashed+=1
                runtime=str(item).startswith(('agent/','scripts/')) or target.name.casefold() in {'zenith','zenith.exe','zenith-serve','zenith-serve.exe'}
                if runtime and target.suffix not in {'.pyc','.pyo'}:errors.append('Runtime file has no recorded checksum: '+str(item))
                continue
            if item.hash.mode not in {'sha256','sha384','sha512'}:errors.append('Unsupported checksum: '+str(item));continue
            checked+=1
            actual=base64.urlsafe_b64encode(file_digest(target,item.hash.mode)).decode().rstrip('=')
            if actual!=item.hash.value or (item.size is not None and target.stat().st_size!=item.size):errors.append('Modified: '+str(item))
    except (OSError,ValueError,TypeError,importlib.metadata.PackageNotFoundError) as exc:
        errors.append('Cannot verify installed inventory: '+type(exc).__name__)
    return report('installed-wheel',checked,errors,unhashed_metadata_or_generated_files=unhashed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,help='Verify a source checkout or extracted ZIP against its release manifest')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    value=verify_source(args.source) if args.source is not None else verify_installed()
    if args.json:print(json.dumps(value,indent=2))
    else:
        print(('PASS' if value['ok'] else 'FAIL')+f" · Zenith {__version__} · {value['checked_files']} files checked ({value['scope']})")
        for error in value['errors']:print(error)
        print(value['note'])
    return 0 if value['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
