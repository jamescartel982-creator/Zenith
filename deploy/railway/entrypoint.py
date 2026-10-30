"""Opt-in one-time private migration and unchanged origin, all as UID 1000.

Used only by a private deployment image containing an encrypted state bundle.
The public Dockerfile never embeds private model state or decryption keys.
"""
import hashlib
import json
import os
from pathlib import Path
import sys


def persistent_cache(root):
    cache = Path(root) / 'huggingface'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Configure before importing Settings/Transformers/Hugging Face constants.
    os.environ['HF_HOME'] = str(cache)
    return cache


def start():
    from scripts.restore_hosting_state import restore
    os.umask(0o077)
    if os.getuid() != 1000:
        raise ValueError('Run the complete migration and Zenith without root privileges')
    root = Path('/app/data')
    destination = root / 'profile'
    key = os.environ.pop('ZENITH_RESTORE_KEY', '')
    checksum = os.environ.pop('ZENITH_RESTORE_SHA256', '')
    restored = restore('/opt/zenith-hosting/state.enc', destination, key, checksum)
    del key
    persistent_cache(root)
    print(json.dumps({'event':'zenith.hosting.state', 'state_restored':restored,
        'uid':os.getuid()}), flush=True)
    # Bootstrap may fetch only the same pinned, hash-checked base artifacts.
    # Native inference runs offline after exec, with no restore key in its env.
    os.environ['HF_HUB_OFFLINE'] = '0'
    from agent.config import Settings
    from agent.deployment import validate_activation
    from agent.cloudflare_origin import CloudflareOrigin
    from agent.checkpoints import tokenizer_signature
    from agent.tokenization import load_preserved_tokenizer
    settings = Settings()
    if settings.provider != 'huggingface' or not settings.adapter or not settings.checkpoint_receipt:
        raise ValueError('Restore and select the existing trained checkpoint before hosting')
    validate_activation(settings)
    if len(settings.api_token) < 32 or settings.api_token == os.getenv('ZENITH_ORIGIN_SECRET', ''):
        raise ValueError('Configure independent strong server and origin credentials')
    CloudflareOrigin(None, os.environ.get('ZENITH_ORIGIN_SECRET', ''), settings.allowed_hosts)
    expected = json.loads(Path('/opt/zenith-hosting/model-identity.json').read_text())
    if settings.model != expected['model'] or settings.revision != expected['revision']:
        raise ValueError('Base selection differs from preserved identity')
    from huggingface_hub import snapshot_download
    snapshot = Path(snapshot_download(settings.model, revision=settings.revision,
        allow_patterns=[row['name'] for row in expected['files']]))
    for row in expected['files']:
        name = row['name']
        if Path(name).name != name:
            raise ValueError('Invalid base artifact name')
        path = snapshot / name
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if path.stat().st_size != row['bytes'] or digest.hexdigest() != row['sha256']:
            raise ValueError('Pinned base artifact integrity differs')
    tokenizer = load_preserved_tokenizer(settings.model, revision=settings.revision, local_files_only=True)
    if tokenizer_signature(tokenizer) != expected['tokenizer_sha256']:
        raise ValueError('Preserved tokenizer identity differs')
    del tokenizer
    os.environ['HF_HUB_OFFLINE'] = '1'
    print(json.dumps({'event':'zenith.hosting.ready', 'state_restored':restored,
        'checkpoint_verified':True, 'base_artifacts_verified':True, 'uid':os.getuid()}), flush=True)
    os.execvpe(sys.executable, [sys.executable, '-m', 'agent.cloudflare_origin',
        '--host', '0.0.0.0', '--require-checkpoint'], dict(os.environ))


if __name__ == '__main__':
    try:
        start()
    except Exception as error:
        # No exception values, file contents, keys or traceback in deploy logs.
        print(json.dumps({'event':'zenith.hosting.failed', 'error_type':type(error).__name__}), flush=True)
        raise SystemExit(1) from None
