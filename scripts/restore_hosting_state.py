"""Administrator-run, authenticated restoration into a new private directory.

Encrypted deployment bundles are not source releases. This module never selects
a model, changes an approval receipt, or overwrites existing application state.
"""
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

MAX_ARCHIVE = 192 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
MAX_FILES = 4096


def digest(data):
    return hashlib.sha256(data).hexdigest()


def restore(archive, destination, key, expected_sha256):
    """Return False for existing state; otherwise authenticate, check, then rename.

    The caller owns the destination parent and must stop other writers during
    restoration. This is not an HTTP endpoint or a model-accessible tool.
    """
    from cryptography.fernet import Fernet, InvalidToken
    archive, destination = Path(archive), Path(destination)
    if destination.exists() or destination.is_symlink():
        return False
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Invalid encrypted state archive')
    encrypted = archive.read_bytes()
    if not isinstance(expected_sha256, str) or digest(encrypted) != expected_sha256:
        raise ValueError('Encrypted state archive checksum differs')
    try:
        clear = Fernet(key).decrypt(encrypted)
    except (InvalidToken, ValueError, TypeError):
        raise ValueError('State archive authentication failed') from None
    if len(clear) > MAX_EXPANDED:
        raise ValueError('State archive exceeds its expansion limit')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.zenith-state-', dir=destination.parent))
    try:
        with zipfile.ZipFile(BytesIO(clear)) as bundle:
            rows = bundle.infolist()
            if not 2 <= len(rows) <= MAX_FILES or sum(row.file_size for row in rows) > MAX_EXPANDED:
                raise ValueError('Invalid state archive size')
            names = [row.filename for row in rows]
            if len(set(names)) != len(names) or names.count('manifest.json') != 1:
                raise ValueError('Invalid state archive inventory')
            if bundle.getinfo('manifest.json').file_size > 1024 * 1024:
                raise ValueError('Oversized state manifest')
            manifest = json.loads(bundle.read('manifest.json'))
            files = manifest.get('files')
            if manifest.get('schema_version') != 1 or not isinstance(files, dict):
                raise ValueError('Invalid state manifest')
            if set(names) != {'manifest.json', *('profile/' + name for name in files)}:
                raise ValueError('State archive inventory differs')
            for name, expected in files.items():
                if not isinstance(name, str) or not name or len(name) > 1024 or any(c in name for c in ('\\', '\x00', ':')):
                    raise ValueError('Unsafe state archive path')
                path = PurePosixPath(name)
                if path.is_absolute() or any(part in {'.', '..'} for part in path.parts) or str(path) != name:
                    raise ValueError('Unsafe state archive path')
                info = bundle.getinfo('profile/' + name)
                mode = info.external_attr >> 16
                if info.is_dir() or (stat.S_IFMT(mode) and not stat.S_ISREG(mode)):
                    raise ValueError('State archive must contain regular files only')
                if (not isinstance(expected, dict) or type(expected.get('bytes')) is not int
                        or expected['bytes'] != info.file_size or not isinstance(expected.get('sha256'), str)):
                    raise ValueError('Invalid state artifact inventory')
                target = temporary.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                checksum = hashlib.sha256()
                total = 0
                with bundle.open(info) as source, target.open('xb') as output:
                    while chunk := source.read(64 * 1024):
                        total += len(chunk)
                        if total > expected['bytes']:
                            raise ValueError('State artifact exceeds declared size')
                        checksum.update(chunk)
                        output.write(chunk)
                target.chmod(0o600)
                if total != expected['bytes'] or checksum.hexdigest() != expected['sha256']:
                    raise ValueError('State artifact checksum differs')
        # Do not replace another writer's state, including an empty directory.
        if destination.exists() or destination.is_symlink():
            raise ValueError('State destination changed during restoration')
        os.rename(temporary, destination)
        return True
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
