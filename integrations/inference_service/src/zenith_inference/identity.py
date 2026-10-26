"""Capture and verify exact trained artifacts without activating or rewriting them."""
import hashlib
import json
from pathlib import Path
import re

from zenith_integrations.shared.secrets import read_json, write_private_new


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def capture(settings, output):
    if settings.provider != 'huggingface' or not re.fullmatch(r'[a-f0-9]{40}', settings.revision):
        raise ValueError('Select the existing Hugging Face model with an exact pinned revision')
    if settings.checkpoint_receipt:
        from agent.deployment import validate_activation
        validate_activation(settings)
    from huggingface_hub import snapshot_download
    from agent.models import WEIGHT_PATTERNS
    from agent.tokenization import load_preserved_tokenizer
    from agent.checkpoints import tokenizer_signature
    snapshot = Path(snapshot_download(settings.model, revision=settings.revision,
                    local_files_only=True, allow_patterns=WEIGHT_PATTERNS)).resolve()
    destination = Path(output).expanduser().resolve()
    protected = [snapshot]
    if settings.adapter:
        protected.append(Path(settings.adapter).expanduser().resolve())
    if any(destination.is_relative_to(root) for root in protected):
        raise ValueError('Service configuration must be outside the original checkpoint directories')
    files = []
    for group, directory in [('base', snapshot), ('adapter', Path(settings.adapter).expanduser().resolve() if settings.adapter else None)]:
        if directory is None:
            continue
        for file in sorted(directory.rglob('*')):
            if file.is_file() and '.git' not in file.parts:
                digest = sha256(file)
                target = file.resolve()
                if group == 'base' and re.fullmatch(r'[a-f0-9]{64}', target.name) and digest != target.name:
                    raise ValueError('Cached base artifact failed its content hash')
                files.append({'group': group, 'path': str(file.absolute()), 'bytes': file.stat().st_size, 'sha256': digest})
    if not any(f['group'] == 'base' and f['path'].endswith('.safetensors') for f in files):
        raise ValueError('Existing safetensors base weights are required')
    if settings.adapter and not any(f['group'] == 'adapter' and f['path'].endswith('adapter_model.safetensors') for f in files):
        raise ValueError('The selected adapter is missing; refusing a base-only substitution')
    tokenizer = load_preserved_tokenizer(settings.model, revision=settings.revision, local_files_only=True)
    fingerprint = tokenizer_signature(tokenizer)
    if settings.adapter:
        adapter_tokenizer = load_preserved_tokenizer(settings.adapter, local_files_only=True)
        if tokenizer_signature(adapter_tokenizer) != fingerprint:
            raise ValueError('Adapter and base tokenizer differ')
    value = {'schema_version': 1, 'model': settings.model, 'revision': settings.revision,
             'base_directory': str(snapshot), 'adapter': str(Path(settings.adapter).expanduser().resolve()) if settings.adapter else '',
             'checkpoint_receipt': settings.checkpoint_receipt, 'tokenizer_sha256': fingerprint,
             'context_tokens': settings.context_tokens, 'max_new_tokens': settings.max_new_tokens,
             'device': settings.device, 'cpu_threads': settings.cpu_threads, 'files': files}
    write_private_new(output, json.dumps(value, indent=2) + '\n')
    return value


def verify(path):
    value = read_json(path)
    if value.get('schema_version') != 1 or not re.fullmatch(r'[a-f0-9]{40}', value.get('revision', '')):
        raise ValueError('Invalid checkpoint identity manifest')
    if not value.get('files') or not re.fullmatch(r'[a-f0-9]{64}', value.get('tokenizer_sha256', '')):
        raise ValueError('Incomplete checkpoint identity manifest')
    if len(value['files']) > 4096:
        raise ValueError('Checkpoint manifest is too large')
    groups = set()
    paths = set()
    roots = {'base': Path(value['base_directory']), 'adapter': Path(value['adapter']) if value.get('adapter') else None}
    if any(root is not None and (not root.is_absolute() or not root.is_dir()) for root in roots.values()):
        raise ValueError('Checkpoint directories must be absolute and available')
    for row in value['files']:
        file = Path(row['path'])
        root = roots.get(row['group'])
        if root is None or not file.is_relative_to(root) or str(file) in paths:
            raise ValueError('Manifest artifacts do not belong to the selected checkpoint')
        paths.add(str(file))
        if not file.is_absolute() or not file.is_file() or file.stat().st_size != row['bytes'] or sha256(file) != row['sha256']:
            raise ValueError('Trained checkpoint artifact integrity check failed')
        groups.add(row['group'])
    expected = {str(file.absolute()) for root in roots.values() if root is not None
                for file in root.rglob('*') if file.is_file() and '.git' not in file.parts}
    if expected != paths:
        raise ValueError('Checkpoint manifest must cover all selected artifacts')
    if 'base' not in groups or (value.get('adapter') and 'adapter' not in groups):
        raise ValueError('Checkpoint identity cannot drop the selected base or adapter')
    # Manifest content, excluding local paths, is safe for public provenance.
    identity_hash = hashlib.sha256(json.dumps({k: value[k] for k in ['model', 'revision', 'tokenizer_sha256']} |
        {'artifacts': sorted((r['group'], Path(r['path']).name, r['sha256']) for r in value['files'])}, sort_keys=True).encode()).hexdigest()
    return value, identity_hash
