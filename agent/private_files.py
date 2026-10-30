"""Bounded owner-file reads without following symlinks; no secret logging."""
import os
from pathlib import Path
import stat


def read_private(path, maximum=4096):
    path = Path(path)
    # lstat also provides a useful fail-closed check on platforms without O_NOFOLLOW.
    if stat.S_ISLNK(path.lstat().st_mode):
        raise PermissionError('A private secret file cannot be a symbolic link')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise PermissionError('Use a bounded regular private secret file')
        if os.name == 'posix':
            if info.st_uid != os.getuid():
                raise PermissionError('Private secret files must belong to the running user')
            os.fchmod(handle.fileno(), stat.S_IMODE(info.st_mode) & 0o600)
        value = handle.read(maximum + 1)
        if len(value) > maximum:
            raise PermissionError('Private secret file exceeded its size limit')
        return value
