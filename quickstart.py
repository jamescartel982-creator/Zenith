#!/usr/bin/env python3
"""Download, verify, install, and launch Zenith using only Python's standard library."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

MAX_ARCHIVE = 128 * 1024**2
MAX_EXPANDED = 512 * 1024**2
REQUIRED = {'agent/__init__.py','README.md','LICENSE','pyproject.toml',
            'install.py','install.sh','install.ps1','run.sh','run.ps1'}


def relative_path(name):
    if not isinstance(name,str) or not name or len(name)>1024 or '\\' in name or ':' in name or any(ord(c)<32 for c in name):
        raise ValueError('Invalid archive or manifest path')
    value=PurePosixPath(name)
    if not value.parts or value.is_absolute() or '..' in value.parts:raise ValueError('Path leaves the installation directory')
    for part in value.parts:
        if part.rstrip(' .')!=part or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',part.split('.')[0],re.I):
            raise ValueError('Non-portable or reserved filesystem path')
    return value


def verify_source(root):
    root=Path(root).resolve();path=root/'release-manifest.json'
    if path.stat().st_size>2*1024**2:raise ValueError('Oversized release manifest')
    manifest=json.loads(path.read_text(encoding='utf-8'))
    rows=manifest.get('files')
    if manifest.get('schema_version')!=1 or not isinstance(rows,list) or not 1<=len(rows)<=20000:
        raise ValueError('Invalid release manifest')
    seen=set()
    for row in rows:
        name=row['path'];pure=relative_path(name);target=(root/Path(*pure.parts)).resolve()
        if root not in target.parents or name in seen or name=='release-manifest.json':raise ValueError('Unsafe or duplicate manifest entry')
        seen.add(name)
        if not re.fullmatch(r'[a-f0-9]{64}',row['sha256']) or type(row['size']) is not int or row['size']<0:
            raise ValueError('Invalid file checksum or size')
        normalization=row.get('normalization','raw')
        if normalization=='lf':
            if target.stat().st_size>64*1024**2:raise ValueError('Oversized text file')
            data=target.read_bytes().replace(b'\r\n',b'\n');size=len(data);digest=hashlib.sha256(data).hexdigest()
        elif normalization=='raw':
            size=target.stat().st_size;hasher=hashlib.sha256()
            with target.open('rb') as handle:
                for block in iter(lambda:handle.read(1024**2),b''):hasher.update(block)
            digest=hasher.hexdigest()
        else:raise ValueError('Unsupported checksum normalization')
        if size!=row['size'] or digest!=row['sha256']:raise ValueError('Changed or incomplete source file: '+name)
    if REQUIRED-seen:raise ValueError('Required installation files are missing from the manifest')
    return manifest


def download_archive(destination,ref='main'):
    if not re.fullmatch(r'[A-Za-z0-9_./-]{1,200}',ref) or '..' in ref:
        raise ValueError('Invalid GitHub revision')
    url='https://codeload.github.com/n8storm/Zenith/zip/'+quote(ref,safe='')
    request=Request(url,headers={'User-Agent':'Zenith-terminal-installer'})
    with urlopen(request,timeout=60) as response,Path(destination).open('xb') as output:
        size=0
        while True:
            chunk=response.read(1024**2)
            if not chunk:break
            size+=len(chunk)
            if size>MAX_ARCHIVE:raise ValueError('Source archive exceeds the download limit')
            output.write(chunk)


def extract_archive(archive,destination):
    destination=Path(destination).resolve();seen=set();roots=set();expanded=0
    with zipfile.ZipFile(archive) as source:
        members=source.infolist()
        if not members or len(members)>20000:raise ValueError('Unexpected source archive file count')
        for member in members:
            # ZipInfo may normalize backslashes on Windows. Validate the original
            # name so archive acceptance is identical on both platforms.
            path=relative_path(member.orig_filename)
            if len(path.parts)<2 and not member.is_dir():raise ValueError('Archive has no repository root')
            roots.add(path.parts[0]);expanded+=member.file_size
            if expanded>MAX_EXPANDED or stat.S_ISLNK(member.external_attr>>16):raise ValueError('Unsafe or oversized source archive')
            if len(path.parts)<2:continue
            name=PurePosixPath(*path.parts[1:]).as_posix();key=name.casefold()
            if key in seen:raise ValueError('Duplicate archive path')
            seen.add(key);target=(destination/Path(*path.parts[1:])).resolve()
            if destination not in target.parents:raise ValueError('Archive path leaves the staging directory')
            if member.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.open(member) as incoming,target.open('xb') as output:shutil.copyfileobj(incoming,output)
            if member.external_attr>>16 & 0o111:target.chmod(0o755)
    if len(roots)!=1:raise ValueError('Archive contains multiple repositories')
    verify_source(destination)


def prepare_source(directory,ref='main'):
    target=Path(directory).expanduser().resolve()
    if target.exists():
        # Resume a verified installation without overwriting code, settings, or data.
        verify_source(target)
        print('Using verified existing Zenith files: '+str(target),flush=True)
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zenith-download-',dir=target.parent) as folder:
        stage=Path(folder);archive=stage/'source.zip';checkout=stage/'checkout';checkout.mkdir()
        print('Downloading Zenith from GitHub...',flush=True)
        download_archive(archive,ref);extract_archive(archive,checkout)
        checkout.rename(target)
    return target


def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path.home()/'Zenith',help='Installation folder (default: ~/Zenith)')
    parser.add_argument('--ref',default='main',help='GitHub revision for a fresh download; existing files are reused')
    parser.add_argument('--activate-candidate',action='store_true',help='Explicitly accept known regressions and select the experimental candidate')
    parser.add_argument('--no-launch',action='store_true',help='Install and cache the model without opening the app')
    parser.add_argument('--mode',choices=['local','ensemble','ollama','localserver'],default='local')
    args=parser.parse_args(argv)
    if sys.version_info<(3,10):parser.error('Python 3.10+ is required; install Python 3.12 and try again')
    if args.activate_candidate and args.mode!='local':parser.error('--activate-candidate requires local mode')
    try:
        root=prepare_source(args.directory,args.ref)
        if args.activate_candidate:
            version=verify_source(root).get('version','')
            match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',version)
            if not match or tuple(map(int,match.groups()))<(0,14,0):
                raise ValueError('This existing checkout predates candidate activation; update it or select a new installation folder')
        command=[sys.executable,str(root/'install.py'),'--mode',args.mode]
        if args.activate_candidate:command.append('--activate-candidate')
        command.append('--download' if args.no_launch else '--launch')
        print('Installing Zenith. The first model download can take several minutes.',flush=True)
        print('Next time: '+('powershell -NoProfile -ExecutionPolicy Bypass -File "'+str(root/'run.ps1')+'" serve --open-browser' if sys.platform=='win32' else 'bash "'+str(root/'start.sh')+'"'),flush=True)
        return subprocess.run(command,cwd=root,check=False).returncode
    except KeyboardInterrupt:
        print('\nStopped. Rerun the same command to resume.',file=sys.stderr);return 130
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:
        print('Setup stopped: '+str(exc)+'. Existing files were preserved. For a changed or older checkout, update it or choose --directory with a new folder.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
