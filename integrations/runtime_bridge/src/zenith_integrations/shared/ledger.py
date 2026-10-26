"""Own durable control ledger. Never migrates or reads native memory databases."""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

APP_ID = 1514295879
TERMINAL = frozenset({'succeeded', 'failed', 'cancelled', 'interrupted'})


class Conflict(ValueError):
    pass


class Ledger:
    def __init__(self, path, audit_key):
        self.path, self.audit_key = Path(path).expanduser().absolute(), audit_key
        if len(audit_key) < 32:
            raise ValueError('Audit authentication needs a separate strong key')
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent = self.path.parent.stat()
        if os.name == 'posix' and (parent.st_uid != os.getuid() or parent.st_mode & 0o077):
            raise ValueError('The bridge ledger needs a private owner-only directory')
        if self.path.is_symlink():
            raise ValueError('Ledger must not be a symlink')
        fresh = False
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            os.close(fd)
            fresh = True
        except FileExistsError:
            info = self.path.stat()
            if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise ValueError('Ledger must be owner-only')
            with sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True) as db:
                if db.execute('PRAGMA application_id').fetchone()[0] != APP_ID:
                    raise ValueError('This is not a bridge control ledger; refusing to alter it')
        with self.connect() as db:
            if fresh:
                db.executescript(f'''
                    PRAGMA application_id={APP_ID};
                    CREATE TABLE jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,session_hash TEXT NOT NULL,
                      request_key TEXT NOT NULL,request_hash TEXT NOT NULL,runtime TEXT NOT NULL,operation TEXT NOT NULL,
                      status TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,result TEXT,error_code TEXT,
                      UNIQUE(user_id,request_key));
                    CREATE TABLE grants(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,session_hash TEXT NOT NULL,
                      capability TEXT NOT NULL,scope TEXT NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE control(name TEXT PRIMARY KEY,value TEXT NOT NULL);
                    INSERT INTO control VALUES('stopped','0');
                    CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,previous TEXT NOT NULL,mac TEXT NOT NULL);
                    PRAGMA user_version=1;
                ''')
            elif db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('Unsupported bridge ledger schema')
        if not self.verify_audit():
            raise ValueError('Bridge audit chain verification failed')

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path, timeout=5, isolation_level=None) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            yield db

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def audit(self, db, action, subject, identifier):
        previous = db.execute('SELECT mac FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
        previous = previous['mac'] if previous else '0' * 64
        event = json.dumps({'action':action, 'subject':subject, 'id':identifier, 'at':time.time()}, sort_keys=True)
        mac = hmac.new(self.audit_key, (previous + event).encode(), hashlib.sha256).hexdigest()
        db.execute('INSERT INTO audit(event,previous,mac) VALUES(?,?,?)', (event,previous,mac))

    def verify_audit(self):
        previous = '0' * 64
        with self.connect() as db:
            for row in db.execute('SELECT event,previous,mac FROM audit ORDER BY seq'):
                expected = hmac.new(self.audit_key, (previous + row['event']).encode(), hashlib.sha256).hexdigest()
                if row['previous'] != previous or not hmac.compare_digest(expected, row['mac']):
                    return False
                previous = row['mac']
        return True

    def admit(self, user, key, request):
        encoded = json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False)
        request_hash = hashlib.sha256(encoded.encode()).hexdigest()
        with self.transaction() as db:
            row = db.execute('SELECT * FROM jobs WHERE user_id=? AND request_key=?',
                (user.id,key)).fetchone()
            if row:
                if row['request_hash'] != request_hash:
                    raise Conflict('Idempotency key belongs to a different request')
                return dict(row), False
            pending = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running','cancel_requested')").fetchone()[0]
            if pending >= 4:
                raise Conflict('Bridge work queue is full')
            identifier, now = uuid.uuid4().hex, time.time()
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (identifier,user.id,user.session_hash,key,request_hash,request['runtime'],request['operation'],'queued',now,now,None,None))
            self.audit(db,'job.admitted',user.id,identifier)
            return dict(db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()), True

    def get(self, identifier, user):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND user_id=?',(identifier,user.id)).fetchone()
        return dict(row) if row else None

    def transition(self, identifier, before, after, result=None, error=None):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()
            if row is None or row['status'] not in before:
                return False
            encoded = json.dumps(result, allow_nan=False) if result is not None else None
            if encoded and len(encoded.encode()) > 1024*1024:
                raise ValueError('Job result exceeds its storage budget')
            db.execute('UPDATE jobs SET status=?,updated=?,result=?,error_code=? WHERE id=?',
                (after,time.time(),encoded,error,identifier))
            self.audit(db,'job.'+after,row['user_id'],identifier)
            return True

    def recover(self):
        # A native timeout is not proof of cancellation. Never replay effects.
        with self.transaction() as db:
            rows = list(db.execute("SELECT id,user_id FROM jobs WHERE status IN ('queued','running','cancel_requested')"))
            for row in rows:
                db.execute("UPDATE jobs SET status='interrupted',updated=?,error_code='restart_reconciliation_required' WHERE id=?",(time.time(),row['id']))
                self.audit(db,'job.interrupted',row['user_id'],row['id'])
        return len(rows)

    def grant(self, user, capability, scope, seconds):
        identifier, expires = uuid.uuid4().hex, time.time()+seconds
        with self.transaction() as db:
            db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?,0)',(identifier,user.id,user.session_hash,capability,json.dumps(scope,sort_keys=True),expires))
            self.audit(db,'grant.created',user.id,identifier)
        return {'id':identifier,'capability':capability,'scope':scope,'expires':expires}

    def allows(self, user, identifier, capability, scope):
        with self.connect() as db:
            row = db.execute('SELECT * FROM grants WHERE id=? AND user_id=? AND session_hash=? AND capability=? AND revoked=0 AND expires>?',
                (identifier,user.id,user.session_hash,capability,time.time())).fetchone()
        return bool(row and json.loads(row['scope']) == scope)

    def revoke(self, user, identifier):
        with self.transaction() as db:
            row = db.execute('SELECT id FROM grants WHERE id=? AND user_id=? AND session_hash=?',
                (identifier,user.id,user.session_hash)).fetchone()
            if row:
                db.execute('UPDATE grants SET revoked=1 WHERE id=?',(identifier,))
                self.audit(db,'grant.revoked',user.id,identifier)
            return bool(row)

    def shutdown(self, user):
        with self.transaction() as db:
            db.execute('UPDATE grants SET revoked=1')
            db.execute("UPDATE control SET value='1' WHERE name='stopped'")
            self.audit(db,'emergency.shutdown',user.id,'all')

    def stopped(self):
        with self.connect() as db:
            return db.execute("SELECT value FROM control WHERE name='stopped'").fetchone()[0] == '1'

    def resume(self, user):
        with self.transaction() as db:
            db.execute("UPDATE control SET value='0' WHERE name='stopped'")
            self.audit(db,'emergency.resume',user.id,'all')
