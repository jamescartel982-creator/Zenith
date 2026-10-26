"""Private secret handles; values never belong in model messages or logs."""
import json
import os
from pathlib import Path
import stat


def read_private(path, maximum=1024 * 1024):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise ValueError('Private configuration must not be a symbolic link')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('Invalid private configuration file')
        if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('Private configuration must be owner-only (chmod 600)')
        with os.fdopen(fd, 'r', encoding='utf-8', closefd=False) as handle:
            value = handle.read(maximum + 1)
        if len(value.encode('utf-8')) > maximum:
            raise ValueError('Private configuration is too large')
        return value
    finally:
        os.close(fd)


def write_private_new(path, value):
    path = Path(path).expanduser().absolute()
    if not path.parent.exists():
        path.parent.mkdir(mode=0o700, parents=True)
    parent = path.parent.stat()
    if os.name == 'posix' and (parent.st_uid != os.getuid() or parent.st_mode & 0o022):
        raise ValueError('Private configuration needs an owned non-writable parent')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def read_json(path):
    return json.loads(read_private(path))
