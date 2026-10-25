"""Metadata-only HMAC audit chain. Export anchors separately to detect truncation."""
import hashlib
import hmac
import os
import secrets
import stat
import time

from .platform_repository import canonical

FIELDS = {'user_id', 'task_id', 'tool', 'step', 'args_hash', 'status', 'reason', 'approval_id'}


class AuditChain:
    def __init__(self, store):
        self.store = store
        path = store.path.parent / 'platform-audit.key'
        with store.connect() as db:
            used = db.execute('SELECT 1 FROM platform_audit LIMIT 1').fetchone() is not None
        if used and not path.exists():
            raise ValueError('Restore the original platform audit key; do not reset existing history')
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(secrets.token_bytes(32))
                handle.flush()
                os.fsync(handle.fileno())
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or (os.name != 'nt' and path.stat().st_mode & 0o077):
            raise ValueError('Audit key must be a private regular file')
        for _ in range(50):
            self.key = path.read_bytes()
            if len(self.key) == 32:
                break
            time.sleep(0.01)
        if len(self.key) != 32:
            raise ValueError('Audit key is incomplete; restore it')
        if not self.verify()['valid']:
            raise ValueError('Platform audit chain is damaged; inspect the preserved history')

    def append(self, event, metadata, db=None):
        if event not in {'task-created', 'task-state', 'task-cancel', 'tool-intent', 'tool-completed',
                         'approval-requested', 'approval-approved', 'approval-denied', 'authority-revoked'}:
            raise ValueError('Unknown audit event')
        if set(metadata) - FIELDS:
            raise ValueError('Raw prompts, arguments and secrets do not belong in audit metadata')
        encoded = canonical(metadata, 2048)
        def write(connection):
            previous = connection.execute('SELECT sequence,record_hash FROM platform_audit ORDER BY sequence DESC LIMIT 1').fetchone()
            sequence = previous['sequence'] + 1 if previous else 1
            if sequence > 100000:
                raise ValueError('Audit capacity reached; archive and review before further effects')
            prev_hash = previous['record_hash'] if previous else '0' * 64
            created = time.time()
            record = canonical([sequence, created, event, encoded, prev_hash])
            digest = hmac.new(self.key, record.encode(), hashlib.sha256).hexdigest()
            connection.execute('INSERT INTO platform_audit VALUES (?,?,?,?,?,?)',
                               (sequence, created, event, encoded, prev_hash, digest))
            return {'sequence': sequence, 'record_hash': digest}
        if db is not None:
            return write(db)
        with self.store.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            return write(connection)

    def verify(self, anchor=None):
        prev_hash = '0' * 64
        count = 0
        anchor_seen = anchor is None or (anchor == {'sequence': 0, 'record_hash': prev_hash})
        with self.store.connect() as db:
            for row in db.execute('SELECT * FROM platform_audit ORDER BY sequence'):
                count += 1
                record = canonical([row['sequence'], row['created'], row['event'], row['metadata'], prev_hash])
                digest = hmac.new(self.key, record.encode(), hashlib.sha256).hexdigest()
                if row['sequence'] != count or row['previous_hash'] != prev_hash or not hmac.compare_digest(digest, row['record_hash']):
                    return {'valid': False, 'sequence': count}
                prev_hash = digest
                if anchor and anchor.get('sequence') == count and anchor.get('record_hash') == digest:
                    anchor_seen = True
        return {'valid': anchor_seen, 'sequence': count, 'record_hash': prev_hash}
