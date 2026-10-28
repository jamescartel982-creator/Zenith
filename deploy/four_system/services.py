"""Install operator-defined, restartable user services without modifying runtime state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROLES = frozenset({'accounts', 'inference', 'bridge', 'hermes', 'openclaw', 'tradingagents'})
TARGET = 'zenith-platform.target'


def user_unit_directory():
    configured = os.environ.get('XDG_CONFIG_HOME', '')
    root = Path(configured) if configured else Path.home() / '.config'
    if not root.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    return root / 'systemd/user'


def liveness():
    states = {}
    for role in sorted(ROLES):
        try:
            result = subprocess.run(['systemctl', '--user', 'is-active', 'zenith-' + role + '.service'],
                capture_output=True, text=True, timeout=3)
            state = result.stdout.strip()
            states[role] = state if state in {'active', 'inactive', 'failed', 'activating', 'deactivating', 'reloading'} else 'unavailable'
            if result.returncode != 0 and states[role] == 'active':
                states[role] = 'unavailable'
        except (OSError, subprocess.SubprocessError):
            states[role] = 'unavailable'
    healthy = all(state == 'active' for state in states.values())
    print(json.dumps({'processes': states, 'all_active': healthy, 'readiness_verified': False}))
    return 0 if healthy else 1


def quote(value, environment_expansion=False):
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Service values must be nonempty single-line strings')
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return '"' + (escaped.replace('$', '$$') if environment_expansion else escaped) + '"'


def absolute(value, kind):
    quote(value)
    path = Path(value)
    if not path.is_absolute() or not path.exists():
        raise ValueError('Configure an existing absolute ' + kind + ' path')
    if kind == 'directory' and not path.is_dir():
        raise ValueError('Service working directory is not a directory')
    if kind != 'directory' and not path.is_file():
        raise ValueError('Service file is not a regular file')
    return path


def scalar_path(value):
    # These directives take the whole RHS as a path, unlike ExecStart's argv.
    # Quotes would become literal path characters. Reject line-continuation and
    # EnvironmentFile glob syntax; expand no path or environment variables.
    if value != value.strip() or any(c in value for c in '\\*?[]'):
        raise ValueError('Service directive paths cannot contain glob or continuation syntax')
    return value.replace('%', '%%')


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {'schema_version', 'services'} or type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('Unsupported service plan')
    rows = plan['services']
    if not isinstance(rows, dict) or set(rows) != ROLES:
        raise ValueError('Configure all six services: accounts, inference, bridge, Hermes, OpenClaw and TradingAgents')
    secret_files = set()
    for role, row in rows.items():
        required = {'command', 'working_directory', 'environment_file', 'memory_max_mb', 'tasks_max', 'after'}
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError('Invalid service fields for ' + role)
        args = row['command']
        if not isinstance(args, list) or not 1 <= len(args) <= 64:
            raise ValueError('Supply a bounded argv array, never a shell command')
        for arg in args:
            quote(arg)
        executable = absolute(args[0], 'executable')
        if not os.access(executable, os.X_OK):
            raise ValueError('Service executable is not executable')
        absolute(row['working_directory'], 'directory')
        scalar_path(row['working_directory'])
        secret = absolute(row['environment_file'], 'environment')
        scalar_path(row['environment_file'])
        if secret.is_symlink() or secret.stat().st_uid != os.getuid() or stat.S_IMODE(secret.stat().st_mode) & 0o077:
            raise ValueError('Environment files must be owned by the service user and inaccessible to group/others')
        file_identity = (secret.stat().st_dev, secret.stat().st_ino)
        if file_identity in secret_files:
            raise ValueError('Each runtime requires a separate environment file')
        secret_files.add(file_identity)
        for name, lower, upper in [('memory_max_mb', 128, 1048576), ('tasks_max', 16, 65536)]:
            if type(row[name]) is not int or not lower <= row[name] <= upper:
                raise ValueError('Invalid service resource budget')
        after = row['after']
        if not isinstance(after, list) or any(not isinstance(name, str) for name in after) or len(after) != len(set(after)) or any(name not in ROLES or name == role for name in after):
            raise ValueError('Invalid service dependencies')
    visited, active = set(), set()
    def visit(role):
        if role in active:
            raise ValueError('Cyclic service dependencies')
        if role in visited:
            return
        active.add(role)
        for dependency in rows[role]['after']:
            visit(dependency)
        active.remove(role)
        visited.add(role)
    for role in rows:
        visit(role)
    return plan


def units(plan):
    validate(plan)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    header = '# Zenith service plan SHA-256: ' + digest + '\n'
    files = {}
    for role, row in sorted(plan['services'].items()):
        dependencies = ' '.join('zenith-' + name + '.service' for name in row['after'])
        files['zenith-' + role + '.service'] = header + '\n'.join([
            '[Unit]', 'Description=Zenith ' + role, 'PartOf=' + TARGET,
            'StartLimitIntervalSec=120', 'StartLimitBurst=5',
            *(['After=' + dependencies, 'Wants=' + dependencies] if dependencies else []),
            '', '[Service]', 'Type=exec', 'WorkingDirectory=' + scalar_path(row['working_directory']),
            'EnvironmentFile=' + scalar_path(row['environment_file']),
            'ExecStart=' + ' '.join(quote(arg, True) for arg in row['command']),
            'Restart=always', 'RestartSec=5s', 'TimeoutStopSec=180s', 'KillMode=mixed',
            'UMask=0077', 'NoNewPrivileges=yes', 'RestrictSUIDSGID=yes', 'LockPersonality=yes',
            'MemoryMax=' + str(row['memory_max_mb']) + 'M', 'TasksMax=' + str(row['tasks_max']),
            'StandardOutput=journal', 'StandardError=journal', 'SyslogIdentifier=zenith-' + role, '',
        ])
    files['zenith-platform-health.service'] = header + '\n'.join([
        '[Unit]', 'Description=Zenith process liveness check', 'After=' + TARGET, 'PartOf=' + TARGET,
        '', '[Service]', 'Type=oneshot',
        'ExecStart=' + ' '.join(quote(value, True) for value in [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), 'status']),
        'TimeoutStartSec=20s', 'NoNewPrivileges=yes', 'UMask=0077', '',
    ])
    files['zenith-platform-health.timer'] = header + '\n'.join([
        '[Unit]', 'Description=Periodic Zenith process liveness check', 'PartOf=' + TARGET,
        '', '[Timer]', 'OnBootSec=2min', 'OnUnitActiveSec=1min',
        'Unit=zenith-platform-health.service', '',
    ])
    members = ['zenith-' + role + '.service' for role in sorted(ROLES)] + ['zenith-platform-health.timer']
    files[TARGET] = header + '\n'.join([
        '[Unit]', 'Description=Zenith four-runtime platform',
        'Wants=' + ' '.join(members), '', '[Install]', 'WantedBy=default.target', '',
    ])
    return files


def write_units(plan, directory):
    """Never overwrite an existing unit or delete native state during rollback."""
    files = units(plan)
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('Use an operator-owned unit directory, not a symlink')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_uid != os.getuid() or stat.S_IMODE(directory.stat().st_mode) & 0o022:
        raise ValueError('Unit directory must be owned by the service user and not writable by others')
    if any((directory / name).exists() or (directory / name).is_symlink() for name in files):
        raise ValueError('Existing Zenith units require an archived, reviewed upgrade; no files were overwritten')
    created = []
    try:
        for name, content in files.items():
            path = directory / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(fd, 'w') as output:
                output.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return sorted(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('render', 'install', 'status'))
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--start', action='store_true')
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'linux' or os.getuid() == 0:
            raise ValueError('Use a dedicated unprivileged Linux service account')
        if args.action == 'status':
            if args.start or args.plan or args.directory:
                raise ValueError('Status accepts no installation arguments')
            return liveness()
        if not args.plan or (args.action == 'render' and (not args.directory or args.start)):
            raise ValueError('Supply a plan, and an output directory for render')
        plan = json.loads(args.plan.read_text())
        directory = args.directory or user_unit_directory()
        if args.action == 'install' and directory.resolve() != user_unit_directory().resolve():
            raise ValueError('Install uses the actual user unit directory; use render for previews')
        names = write_units(plan, directory)
        if args.action == 'install':
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True, timeout=30)
            if args.start:
                subprocess.run(['systemctl', '--user', 'enable', '--now', TARGET], check=True, timeout=180)
                if liveness() != 0:
                    raise ValueError('Not every runtime process is active')
        print(json.dumps({'units': names, 'start_requested': bool(args.start), 'readiness_verified': False, 'model_files_modified': False}))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError):
        print('Service setup did not complete. Check the plan, private files, unit directory and user systemd manager.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
