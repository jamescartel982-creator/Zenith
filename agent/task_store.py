"""Bounded durable tasks with fenced leases and conservative crash recovery."""
import json
import time
from uuid import uuid4

from .event_bus import TERMINAL, append_event
from .permissions import ActorContext
from .platform_repository import canonical


class CapacityError(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class TaskStore:
    def __init__(self, store, permissions, audit, config):
        self.store, self.permissions, self.audit, self.config = store, permissions, audit, config

    def create(self, actor, kind, payload, conversation_id=None):
        if kind not in {'chat', 'diagnostics'}:
            raise ValueError('Unsupported task kind')
        encoded = canonical(payload, 32000)
        identifier, now = str(uuid4()), time.time()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.permissions.validate(actor, db)
            pending = db.execute("SELECT user_id FROM platform_tasks WHERE status NOT IN ('completed','failed','cancelled','needs_reconciliation')").fetchall()
            if len(pending) >= self.config.max_pending or sum(r['user_id'] == actor.user_id for r in pending) >= self.config.per_user_pending:
                raise CapacityError('Task queue is full; wait or cancel pending work')
            if db.execute('SELECT COUNT(*) FROM platform_tasks').fetchone()[0] >= self.config.max_tasks:
                raise CapacityError('Task retention capacity reached; review retained tasks')
            if conversation_id:
                owner = db.execute('SELECT user_id FROM conversation_owners WHERE session_id=?', (conversation_id,)).fetchone()
                legacy = db.execute('SELECT 1 FROM turns WHERE session_id=? LIMIT 1', (conversation_id,)).fetchone()
                if (owner and owner['user_id'] != actor.user_id) or (not owner and legacy):
                    raise PermissionError('Conversation not owned by this account')
                db.execute('INSERT OR IGNORE INTO conversation_owners VALUES (?,?)', (conversation_id, actor.user_id))
            db.execute('''INSERT INTO platform_tasks
                (id,user_id,session_hash,auth_revision,kind,payload,status,created,updated,deadline,conversation_id)
                VALUES (?,?,?,?,?,?,'queued',?,?,?,?)''',
                (identifier, actor.user_id, actor.session_hash, actor.revision, kind, encoded,
                 now, now, now + self.config.task_seconds, conversation_id))
            append_event(db, identifier, actor.user_id, 'queued', {'status': 'queued'})
            self.audit.append('task-created', {'task_id': identifier, 'user_id': actor.user_id}, db)
        return self.get(actor, identifier)

    def get(self, actor, task_id):
        with self.store.connect() as db:
            self.permissions.validate(actor, db)
            row = db.execute('SELECT * FROM platform_tasks WHERE id=? AND user_id=?', (task_id, actor.user_id)).fetchone()
        if row is None:
            raise LookupError('Task not found')
        return {key: row[key] for key in ('id', 'kind', 'status', 'version', 'created', 'updated', 'deadline', 'error', 'conversation_id', 'cancel_requested')} | {
            'request': json.loads(row['payload']), 'result': json.loads(row['result']) if row['result'] else None}

    def list(self, actor):
        with self.store.connect() as db:
            self.permissions.validate(actor, db)
            return [dict(r) for r in db.execute('''SELECT id,kind,status,created,updated,conversation_id
                FROM platform_tasks WHERE user_id=? ORDER BY created DESC LIMIT 50''', (actor.user_id,))]

    def internal(self, task_id):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM platform_tasks WHERE id=?', (task_id,)).fetchone()
        return dict(row) if row else None

    def _state(self, db, row, status, error=None, result=None):
        db.execute('''UPDATE platform_tasks SET status=?,error=?,result=?,version=version+1,
            lease_owner=NULL,lease_until=NULL,updated=? WHERE id=?''',
            (status, error, canonical(result, 64000) if result is not None else None, time.time(), row['id']))
        metadata = {'status': status}
        if error:
            metadata['reason'] = error
        append_event(db, row['id'], row['user_id'], status, metadata)
        self.audit.append('task-state', {'task_id': row['id'], 'user_id': row['user_id'], **metadata}, db)

    def recover(self):
        """Never replay an ambiguously running effect after a lost worker lease."""
        now = time.time()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute('''SELECT * FROM platform_tasks WHERE
                (status='running' AND lease_until<=?) OR
                (status IN ('queued','waiting_approval') AND deadline<=?)''', (now, now)).fetchall()
            for row in rows:
                status = 'needs_reconciliation' if row['status'] == 'running' else 'failed'
                self._state(db, row, status, 'worker-lease-expired' if status == 'needs_reconciliation' else 'deadline-exceeded')
        return len(rows)

    def claim(self, worker):
        self.recover()
        now = time.time()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM platform_tasks WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return None
            actor = ActorContext(row['user_id'], row['session_hash'], row['auth_revision'])
            try:
                self.permissions.validate(actor, db)
            except PermissionError:
                self._state(db, row, 'failed', 'authorization-expired')
                return None
            db.execute("UPDATE platform_tasks SET status='running',lease_owner=?,lease_until=?,updated=?,version=version+1 WHERE id=?",
                       (worker, now + self.config.lease_seconds, now, row['id']))
            append_event(db, row['id'], row['user_id'], 'running', {'status': 'running'})
            self.audit.append('task-state', {'task_id': row['id'], 'user_id': row['user_id'], 'status': 'running'}, db)
        return self.internal(row['id'])

    def fenced(self, db, task_id, worker, allow_cancel=False):
        row = db.execute('SELECT * FROM platform_tasks WHERE id=?', (task_id,)).fetchone()
        if not row or row['status'] != 'running' or row['lease_owner'] != worker or row['lease_until'] <= time.time():
            raise LeaseLost('Task lease is no longer current')
        if not allow_cancel and (row['cancel_requested'] or row['deadline'] <= time.time()):
            raise LeaseLost('Task was cancelled or exceeded its deadline')
        return row

    def heartbeat(self, task_id, worker):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                self.fenced(db, task_id, worker)
            except LeaseLost:
                return False
            db.execute('UPDATE platform_tasks SET lease_until=? WHERE id=?',
                       (time.time() + self.config.lease_seconds, task_id))
        return True

    def finish(self, task_id, worker, status, result=None, error=None):
        if status not in TERMINAL:
            raise ValueError('Invalid terminal state')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.fenced(db, task_id, worker, allow_cancel=True)
            if status == 'completed' and row['deadline'] <= time.time():
                status, result, error = 'failed', None, 'deadline-exceeded'
            if row['cancel_requested']:
                uncertain = db.execute("SELECT 1 FROM platform_receipts WHERE task_id=? AND status='started'", (task_id,)).fetchone()
                status, result, error = ('needs_reconciliation', None, 'cancelled-with-uncertain-effect') if uncertain else ('cancelled', None, 'cancel-requested')
            self._state(db, row, status, error, result)

    def cancel(self, actor, task_id):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.permissions.validate(actor, db)
            row = db.execute('SELECT * FROM platform_tasks WHERE id=? AND user_id=?', (task_id, actor.user_id)).fetchone()
            if row is None:
                raise LookupError('Task not found')
            if row['status'] in TERMINAL or row['cancel_requested']:
                return
            db.execute('UPDATE platform_tasks SET cancel_requested=1 WHERE id=?', (task_id,))
            if row['status'] != 'running':
                self._state(db, row, 'cancelled', 'cancel-requested')
            else:
                append_event(db, task_id, actor.user_id, 'cancel-requested', {'status': 'cancel-requested'})
            self.audit.append('task-cancel', {'task_id': task_id, 'user_id': actor.user_id}, db)
