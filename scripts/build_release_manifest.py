"""Inventory reviewed, Git-tracked release files; never scan local private data."""
import argparse
import json
from pathlib import Path
import subprocess
from agent import __version__
from agent.integrity import MANIFEST_NAME,source_fingerprint,safe_source_path


def build_manifest(root):
    root=Path(root).resolve()
    names=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode('utf-8').split('\0')[:-1]
    rows=[]
    for name in sorted(names):
        if name==MANIFEST_NAME:continue
        target=safe_source_path(root,name)
        if not target.is_file():raise ValueError('Tracked release file is missing: '+name)
        data=target.read_bytes()
        try:
            data.decode('utf-8');normalization='raw' if b'\0' in data else 'lf'
        except UnicodeDecodeError:normalization='raw'
        size,digest=source_fingerprint(target,normalization)
        rows.append({'path':name,'size':size,'sha256':digest,'normalization':normalization})
    if not rows:raise ValueError('No tracked source files')
    value={'schema_version':1,'version':__version__,'files':rows,
           'manifest_self_excluded':True,'scope':'Every tracked source release file except this manifest itself.',
           'text_line_endings':'UTF-8 text hashes normalize CRLF to LF for Windows/Linux and source ZIP consistency; binary files are exact.',
           'external_weights':'Model-pack manifests inventory 89 separately downloaded weight artifacts; they are not bundled source files.',
           'privacy':'Untracked local settings, accounts, conversations, admin codes, caches and trained artifacts are excluded.'}
    (root/MANIFEST_NAME).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    value=build_manifest(args.root);print(f"Inventoried {len(value['files'])} tracked files for Zenith {__version__}")


if __name__=='__main__':main()
