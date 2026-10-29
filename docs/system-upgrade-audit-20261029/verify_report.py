"""Verify audit evidence and plan consistency without models, secrets or network."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def main():
    folder = Path(__file__).resolve().parent
    inventory = json.loads((folder / 'source-inventory.json').read_text())
    plan = json.loads((folder / 'capabilities.json').read_text())
    validation = json.loads((folder / 'validation.json').read_text())
    benchmark = json.loads((folder / 'current-model-baseline.json').read_text())
    provenance = json.loads((folder / 'github-provenance.json').read_text())
    commit = inventory['commit']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A complete immutable source commit is required')
    if any(value != commit for value in (plan['source_commit'], validation['source_commit'],
                                        benchmark['commit'], provenance['commit'])):
        raise ValueError('Audit artifacts refer to different source baselines')
    # Read immutable Git blobs, not a possibly modified checkout, to verify the
    # original audited bytes even after this documentation package was added.
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', commit]).decode().split('\0')[:-1]
    rows = inventory['files']
    if set(names) != {row['path'] for row in rows} or len(names) != len(rows):
        raise ValueError('The inventory must cover every tracked baseline file exactly once')
    python_count = 0
    for row in rows:
        path = PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in str(path):
            raise ValueError('Unsafe inventory path')
        body = subprocess.check_output(['git', 'cat-file', 'blob', commit + ':' + str(path)])
        if len(body) != row['git_blob_bytes'] or hashlib.sha256(body).hexdigest() != row['git_blob_sha256']:
            raise ValueError('Baseline source hash mismatch: ' + str(path))
        checkout = body
        if row['checkout_line_endings'] == 'crlf':
            checkout = body.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        elif row['checkout_line_endings'] == 'lf':
            checkout = body.replace(b'\r\n', b'\n')
        elif row['checkout_line_endings'] != 'same-as-git':
            raise ValueError('Unsupported checkout transformation')
        if len(checkout) != row['bytes'] or hashlib.sha256(checkout).hexdigest() != row['sha256']:
            raise ValueError('The original checkout hash is not explained by line endings')
        if path.suffix == '.py':
            ast.parse(body, filename=str(path))
            python_count += 1
    capabilities = plan['capabilities']
    by_id = {item['id']: item for item in capabilities}
    if len(capabilities) != 40 or set(by_id) != set(range(1, 41)):
        raise ValueError('The plan must cover all forty distinct capabilities')
    required = {'name', 'status', 'evidence', 'existing', 'work', 'destinations', 'tests',
                'dependencies', 'complexity', 'risk', 'flag', 'milestone', 'acceptance', 'rollback'}
    for item in capabilities:
        if not required <= item.keys() or any(not item[field] for field in required - {'dependencies', 'evidence'}):
            raise ValueError('Incomplete capability plan')
        if item['status'] not in {'EXISTING', 'PARTIAL', 'MISSING'} or set(item['evidence']) - set(names):
            raise ValueError('Unverified existing source claim')
    completed, active = set(), set()
    def visit(identifier):
        if identifier in active:
            raise ValueError('Implementation prerequisite cycle')
        if identifier in completed:
            return
        active.add(identifier)
        for dependency in by_id[identifier]['dependencies']:
            visit(dependency)
        active.remove(identifier)
        completed.add(identifier)
    for identifier in by_id:
        visit(identifier)
    if python_count != inventory['python_files'] or inventory['python_parse_errors']:
        raise ValueError('Python coverage mismatch')
    if sum(row['tests_run'] for row in validation['suites']) != validation['total_tests_run']:
        raise ValueError('Test totals do not match recorded suites')
    if not benchmark['checkpoint_and_profile_unchanged'] or not benchmark['runtime_parameters_unchanged']:
        raise ValueError('The baseline did not preserve the original model/profile')
    advisory = json.loads((folder / 'dependency-advisories.json').read_text())
    skipped = [item for item in advisory['dependencies'] if item.get('skip_reason')]
    if not skipped or skipped[0]['name'] != 'torch':
        raise ValueError('The observed dependency scan gap must remain visible')
    print(json.dumps({'verified_baseline': commit, 'tracked_blobs': len(rows),
                      'python_modules': python_count, 'capabilities': len(capabilities),
                      'prerequisite_graph': 'acyclic', 'recorded_tests': validation['total_tests_run'],
                      'advisory_skips_visible': len(skipped), 'production_changes': False}))


if __name__ == '__main__':
    main()
