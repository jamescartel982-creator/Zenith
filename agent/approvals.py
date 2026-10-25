"""Human decisions bound to exact arguments, session, task and step; single-use."""
import hashlib
import time
from uuid import uuid4

from .event_bus import append_event
from .platform_repository import canonical


def action_hash(tool, arguments):
    return hashlib.sha256(canonical({'version': 1, 'tool': tool, 'arguments': arguments}, 32000).encode()).hexdigest()


class Approvals:
    def __init__(self, tasks, permissions, audit):
        self.tasks, self.store, self.permissions, self.audit = tasks, tasks.store, permissions, audit

    def prepare(self, actor, task_id, worker, step, tool, arguments):
        self.permissions.require_tool(actor, tool)
        digest = action_hash(tool, arguments)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            task = self.tasks.fenced(db, task_id, worker)
            self.permissions.validate(actor, db)
            if task['user_id'] != actor.user_id or task['session_hash'] != actor.session_hash:
                raise PermissionError('Task authority does not match')
            row = db.execute('SELECT * FROM platform_approvals WHERE task_id=? AND step=?', (task_id, step)).fetchone()
            if row:
                if row['args_hash'] != digest or row['tool'] != tool or row['status'] in {'consumed', 'denied'} or row['expires'] <= time.time():
                    raise PermissionError('Action approval is stale or arguments changed')
                if row['status'] == 'approved':
                    return True
            else:
                identifier = str(uuid4())
                db.execute('INSERT INTO platform_approvals VALUES (?,?,?,?,?,?,?,?,?,?)',
                           (identifier, task_id, step, actor.user_id, actor.session_hash, tool, digest,
                            'pending', min(time.time() + 300, task['deadline']), time.time()))
                self.audit.append('approval-requested', {'task_id': task_id, 'user_id': actor.user_id,
                    'tool': tool, 'args_hash': digest, 'approval_id': identifier, 'step': step}, db)
            self.tasks._state(db, task, 'waiting_approval')
        return False

    def decide(self, actor, approval_id, approved):
        if type(approved) is not bool:
            raise ValueError('Approval decision must be boolean')
        self.permissions.require_owner(actor)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.permissions.validate(actor, db)
            row = db.execute('SELECT * FROM platform_approvals WHERE id=? AND user_id=? AND session_hash=?',
                             (approval_id, actor.user_id, actor.session_hash)).fetchone()
            if row is None:
                raise LookupError('Approval not found')
            task = db.execute('SELECT * FROM platform_tasks WHERE id=?', (row['task_id'],)).fetchone()
            if row['status'] != 'pending' or row['expires'] <= time.time() or task['status'] != 'waiting_approval' or task['cancel_requested'] or task['auth_revision'] != actor.revision:
                raise PermissionError('Approval is no longer pending')
            self.permissions.require_tool(actor, row['tool'])
            status = 'approved' if approved else 'denied'
            db.execute('UPDATE platform_approvals SET status=? WHERE id=?', (status, approval_id))
            self.audit.append('approval-' + status, {'task_id': task['id'], 'user_id': actor.user_id, 'approval_id': approval_id}, db)
            self.tasks._state(db, task, 'queued' if approved else 'cancelled', None if approved else 'approval-denied')

    def consume(self, db, actor, task_id, step, tool, arguments):
        self.permissions.validate(actor, db)
        self.permissions.require_tool(actor, tool)
        row = db.execute('''SELECT * FROM platform_approvals WHERE task_id=? AND step=? AND user_id=?
            AND session_hash=?''', (task_id, step, actor.user_id, actor.session_hash)).fetchone()
        if not row or row['status'] != 'approved' or row['expires'] <= time.time() or row['tool'] != tool or row['args_hash'] != action_hash(tool, arguments):
            raise PermissionError('Exact current action approval required')
        db.execute("UPDATE platform_approvals SET status='consumed' WHERE id=?", (row['id'],))

    def list(self, actor, task_id):
        self.tasks.get(actor, task_id)
        with self.store.connect() as db:
            self.permissions.validate(actor, db)
            return [dict(r) for r in db.execute('''SELECT id,step,tool,args_hash,status,expires FROM platform_approvals
                WHERE task_id=? AND user_id=? ORDER BY step''', (task_id, actor.user_id))]
