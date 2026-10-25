"""One database owner, consistent backups and canonical bounded JSON."""
import json
import os
from pathlib import Path
import sqlite3


def canonical(value, max_bytes=65536):
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(encoded.encode()) > max_bytes:
        raise ValueError('Structured data exceeds its byte budget')
    return encoded


def backup(store, destination):
    destination = Path(destination).expanduser().resolve()
    if destination == store.path.resolve() or destination.exists():
        raise ValueError('Backup needs a new destination outside the live database')
    # Exclusive creation prevents accidental replacement; SQLite backup includes WAL data.
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with store.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup integrity verification failed')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination
