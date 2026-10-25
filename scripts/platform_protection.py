"""Read-only model/profile protection receipts; receipts contain hashes, not secrets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def capture(settings, profile=None):
    root = Path(__file__).resolve().parents[1]
    adapter = Path(settings.adapter).expanduser() if settings.adapter else None
    files = {}
    if adapter:
        if not adapter.is_dir() or adapter.is_symlink():
            raise ValueError('The selected adapter must be an existing directory')
        for path in sorted(adapter.rglob('*')):
            if path.is_symlink():
                raise ValueError('Adapter receipts do not follow symbolic links')
            if path.is_file():
                files[str(path.relative_to(adapter))] = fingerprint(path)
    return {
        'format': 1,
        'source_commit': subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
        'model': settings.model, 'revision': settings.revision,
        'adapter_files': files,
        'profile_sha256': fingerprint(profile) if profile and Path(profile).is_file() else None,
    }


def compare(before, after):
    # Code commits are expected to change during implementation; model/profile are not.
    return all(before.get(key) == after.get(key) for key in (
        'model', 'revision', 'adapter_files', 'profile_sha256'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--compare')
    args = parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    settings = Settings()
    output = Path(args.output).expanduser().resolve()
    profile = config_file().resolve()
    if output == profile or (settings.adapter and output.is_relative_to(Path(settings.adapter).resolve())):
        parser.error('Receipts must be outside protected profile/model paths')
    receipt = capture(settings, profile)
    if args.compare and not compare(json.loads(Path(args.compare).read_text()), receipt):
        parser.error('Protected model or profile changed')
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Protection receipt written; no model files changed.')


if __name__ == '__main__':
    main()
