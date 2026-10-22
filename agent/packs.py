"""Complete pinned model inventories and verified, credential-free downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.parse import quote
import requests
from .paths import zenith_home, config_file

PACK_ROOT = Path(__file__).parent / 'model_packs'


def manifests():
    return [json.loads(path.read_text(encoding='utf-8')) for path in sorted(PACK_ROOT.glob('*.json'))]


def summaries():
    return [{key: pack[key] for key in ('id', 'name', 'source_repo', 'source_url', 'revision', 'license', 'file_count', 'total_bytes', 'recommended_file', 'runtime_requirements', 'status')} for pack in manifests()]


def get_pack(identifier):
    return next((pack for pack in manifests() if pack['id'] == identifier), None)


def destination(root, name):
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or '\\' in name or ':' in name:
        raise ValueError('Invalid manifest file path')
    target = (root / Path(*parts.parts)).resolve()
    if root.resolve() not in target.parents:
        raise ValueError('File path leaves the model directory')
    return target


def verify_file(path, spec):
    if not path.is_file() or path.stat().st_size != spec['size']:
        return False
    digest = hashlib.sha256() if spec.get('sha256') else hashlib.sha1()
    if not spec.get('sha256'):
        digest.update(b'blob ' + str(spec['size']).encode() + b'\0')
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest() == (spec.get('sha256') or spec['git_blob_sha1'])


def download_file(pack, spec, root):
    target = destination(root, spec['path'])
    if verify_file(target, spec):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    url = 'https://huggingface.co/' + pack['source_repo'] + '/resolve/' + pack['revision'] + '/' + quote(spec['path'], safe='/')
    temporary = None
    try:
        # Public, pinned URLs only; do not read HF_TOKEN or send Authorization.
        with requests.get(url, stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.zenith-download-', delete=False) as handle:
                temporary = Path(handle.name)
                count = 0
                for chunk in response.iter_content(4 * 1024 * 1024):
                    count += len(chunk)
                    if count > spec['size']:
                        raise ValueError('Upstream file exceeds its pinned size')
                    handle.write(chunk)
        if not verify_file(temporary, spec):
            raise ValueError('File failed its pinned size/checksum verification')
        os.replace(temporary, target)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def select_files(pack, all_files=False, support_only=False, filename=None):
    if all_files:
        return pack['files']
    if support_only:
        return [row for row in pack['files'] if row['kind'] == 'support']
    name = filename or pack['recommended_file']
    if not name:
        raise ValueError('This pack needs a specialized runtime; select --all, --support-only, or an explicit --file')
    rows = [row for row in pack['files'] if row['path'] == name]
    if not rows:
        raise ValueError('Requested file is not in this pinned manifest')
    return rows


def configure(pack, endpoint, model_alias='zenith', overwrite=False):
    from .config import Settings
    Settings(provider='localserver', local_server_url=endpoint)
    path = config_file()
    if path.exists() and not overwrite:
        raise ValueError('A profile exists; use --overwrite-config to replace it deliberately')
    if not model_alias or any(c in model_alias for c in '\r\n') or len(model_alias) > 200:
        raise ValueError('Invalid local server model alias')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Zenith local model server. Source provenance is retained in the pinned pack manifest.\n'
                    f'AI_PROVIDER=localserver\nZENITH_MODEL_LABEL={pack["name"]}\n'
                    f'ZENITH_LOCAL_SERVER_URL={endpoint}\nZENITH_LOCAL_SERVER_MODEL={model_alias}\n'
                    'CONTEXT_TOKENS=8192\nMAX_NEW_TOKENS=2048\nTEMPERATURE=0.7\n', encoding='utf-8')
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'files', 'download', 'verify', 'configure'], nargs='?', default='list')
    parser.add_argument('pack', nargs='?')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--all', action='store_true', help='Every pinned file, including every alternative quantization')
    selection.add_argument('--support-only', action='store_true', help='All source/support files, without weights')
    selection.add_argument('--file', help='One exact filename from the manifest')
    parser.add_argument('--directory', type=Path, help='Default: ZENITH_HOME/models/<pack>')
    parser.add_argument('--endpoint', default='http://127.0.0.1:8080/v1')
    parser.add_argument('--model-alias', default='zenith')
    parser.add_argument('--overwrite-config', action='store_true')
    args = parser.parse_args()
    if args.action == 'list':
        print(json.dumps(summaries(), indent=2))
        return 0
    pack = get_pack(args.pack)
    if pack is None:
        parser.error('Select one of: ' + ', '.join(pack['id'] for pack in manifests()))
    if args.action == 'files':
        print(json.dumps(pack, indent=2))
        return 0
    try:
        if args.action == 'configure':
            print('Saved ' + str(configure(pack, args.endpoint, args.model_alias, args.overwrite_config)))
            print('Start the local model server separately, then restart Zenith. Existing environment/.env overrides still apply.')
            return 0
        rows = select_files(pack, args.all, args.support_only, args.file)
        root = (args.directory or zenith_home() / 'models' / pack['id']).expanduser().resolve()
        if args.action == 'verify':
            failed = 0
            for row in rows:
                valid = verify_file(destination(root, row['path']), row)
                print(('OK ' if valid else 'MISSING/INVALID ') + row['path'])
                failed += not valid
            return int(failed > 0)
        root.mkdir(parents=True, exist_ok=True)
        required = sum(row['size'] for row in rows if not verify_file(destination(root, row['path']), row))
        print(f'{pack["name"]}: {len(rows)} files, {sum(row["size"] for row in rows) / 2**30:.2f} GiB selected', flush=True)
        if shutil.disk_usage(root).free < required + 256 * 1024**2:
            raise ValueError('Insufficient free disk space for selected files; choose one quantization or another --directory')
        for row in rows:
            print('Checking/downloading ' + row['path'], flush=True)
            download_file(pack, row, root)
        print('All selected files passed pinned integrity verification. No upstream code was executed.')
        return 0
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f'Pack operation failed ({type(exc).__name__}): {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
