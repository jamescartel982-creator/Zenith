"""Inspect and cache configured weights without executing remote model code."""
import argparse
import json
from pathlib import Path
from .config import Settings

WEIGHT_PATTERNS = ['*.json', '*.safetensors', '*.model', '*.tiktoken', 'tokenizer.*',
                   'merges.txt', 'vocab.txt', 'README.md', 'LICENSE*', 'NOTICE*']


def model_specs(settings):
    if settings.provider == 'ensemble':
        from .ensemble import EnsembleProvider
        return [member.public() | {'revision': member.revision, 'adapter': member.adapter, 'base_url': member.base_url or settings.ollama_url}
                for member in EnsembleProvider(settings).members]
    return [{'id': 'primary', 'name': settings.model_name, 'provider': settings.provider,
             'model': settings.model_name, 'revision': settings.revision, 'adapter': settings.adapter}]


def cache_status(spec):
    if spec['provider'] == 'tiny':
        present = Path(spec['model']).expanduser().is_file()
        return {'cached': present, 'reason': 'Checkpoint found' if present else 'Tiny checkpoint is missing; train or select it first'}
    if spec['provider'] != 'huggingface':
        return {'cached': None, 'reason': 'Managed by ' + spec['provider']}
    try:
        model_path = Path(spec['model']).expanduser()
        if not model_path.is_dir():
            from huggingface_hub import snapshot_download
            model_path = Path(snapshot_download(spec['model'], revision=spec['revision'], local_files_only=True))
        missing = [name for name in ['config.json', 'tokenizer_config.json'] if not (model_path / name).is_file()]
        index = model_path / 'model.safetensors.index.json'
        if index.exists():
            shards = set(json.loads(index.read_text(encoding='utf-8'))['weight_map'].values())
            if not shards or any(not (model_path / name).is_file() for name in shards):
                missing.append('complete safetensors shards')
        elif not (model_path / 'model.safetensors').is_file():
            missing.append('model.safetensors')
        if not any((model_path / name).is_file() for name in ['tokenizer.json', 'tokenizer.model', 'vocab.json', 'vocab.txt', 'spiece.model']):
            missing.append('tokenizer files')
        return {'cached': not missing, 'reason': 'Ready in local cache' if not missing else 'Missing: ' + ', '.join(missing)}
    except (ImportError, OSError, ValueError, KeyError):
        return {'cached': False, 'reason': 'Weights are not fully cached; run zenith models download'}


def download(spec, offline=False):
    if spec['provider'] == 'huggingface':
        from huggingface_hub import snapshot_download
        snapshot_download(spec['model'], revision=spec['revision'], allow_patterns=WEIGHT_PATTERNS,
                          local_files_only=offline, max_workers=2)
        state = cache_status(spec)
        if not state['cached']:
            raise RuntimeError(state['reason'])
        return state
    if spec['provider'] == 'ollama':
        if offline:
            raise ValueError('Ollama pull is unavailable in offline-check mode')
        import requests
        settings = Settings()
        with requests.post((spec.get('base_url') or settings.ollama_url).rstrip('/') + '/api/pull', json={'model': spec['model'], 'stream': True},
                           stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            previous = None
            for line in response.iter_lines():
                if not line:
                    continue
                row = json.loads(line)
                if row.get('error'):
                    raise RuntimeError('Ollama could not pull the requested model')
                status = row.get('status')
                if status and status != previous:
                    print(status, flush=True)
                    previous = status
        return {'cached': True, 'reason': 'Pull completed in Ollama'}
    raise ValueError('Train or select a local Tiny checkpoint instead of downloading it')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'download', 'check'], nargs='?', default='list')
    parser.add_argument('--member', default=None, help='Only this configured member ID')
    parser.add_argument('--local-files-only', action='store_true', help='Verify existing HF cache without network access')
    args = parser.parse_args()
    settings = Settings()
    specs = model_specs(settings)
    if args.member:
        specs = [spec for spec in specs if spec['id'] == args.member]
        if not specs:
            parser.error('No configured member has that ID')
    failed = False
    seen = set()
    for spec in specs:
        key = (spec['provider'], spec['model'], spec['revision'])
        if key in seen:
            continue
        seen.add(key)
        print(f'{spec["id"]}: {spec["model"]} ({spec["provider"]})', flush=True)
        if args.action == 'download':
            try:
                state = download(spec, offline=args.local_files_only)
            except Exception as exc:
                print(f'Could not cache this model ({type(exc).__name__}). Check network, disk space, access, and provider settings.')
                failed = True
                continue
        else:
            state = cache_status(spec)
        print('  ' + state['reason'])
        if args.action == 'check' and state['cached'] is False:
            failed = True
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
