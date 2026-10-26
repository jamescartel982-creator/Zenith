"""Audit actual selected installed versions, excluding only Zenith's own project.

Requires the optional pip-audit tooling. No advisories are ignored. The pinned
snapshot includes runtime, optional model/data libraries, and installed tooling.
"""
import argparse
from importlib import metadata
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dependency-audit.json'))
    args = parser.parse_args()
    selected = {}
    for distribution in metadata.distributions():
        name = distribution.metadata['Name']
        normalized = re.sub(r'[-_.]+', '-', name).lower()
        if normalized == 'zenith-local':
            continue
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*', name) or not re.fullmatch(r'[a-zA-Z0-9.!+_-]+', distribution.version):
            raise ValueError('Invalid installed package metadata')
        selected.setdefault(normalized, (name, distribution.version))
    with tempfile.TemporaryDirectory(prefix='zenith-dependency-audit-') as directory:
        requirements = Path(directory) / 'installed.txt'
        requirements.write_text(''.join(f'{name}=={version}\n' for name, version in sorted(selected.values())), encoding='utf-8')
        result = subprocess.run([sys.executable, '-m', 'pip_audit', '--no-deps', '--disable-pip',
            '--requirement', str(requirements), '--format', 'json', '--output', str(args.output)], check=False)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
