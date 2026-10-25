"""Scoped durable task events; SSE polling has bounded batches, no lossy queue."""
import asyncio
import json
import time

TERMINAL = {'completed', 'failed', 'cancelled', 'needs_reconciliation'}


class EventBus:
    def __init__(self, store, permissions):
        self.store, self.permissions = store, permissions

    def read(self, actor, task_id, after=0, limit=100):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Invalid event cursor or batch size')
        with self.store.connect() as db:
            self.permissions.validate(actor, db)
            task = db.execute('SELECT status FROM platform_tasks WHERE id=? AND user_id=?', (task_id, actor.user_id)).fetchone()
            if task is None:
                raise LookupError('Task not found')
            rows = db.execute('''SELECT sequence,event,metadata,created FROM platform_events
                WHERE task_id=? AND user_id=? AND sequence>? ORDER BY sequence LIMIT ?''',
                (task_id, actor.user_id, after, limit)).fetchall()
        return {'status': task['status'], 'events': [dict(r) | {'metadata': json.loads(r['metadata'])} for r in rows]}

    async def stream(self, actor, task_id, after, disconnected, seconds=25):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if await disconnected():
                return
            try:
                batch = await asyncio.to_thread(self.read, actor, task_id, after)
            except (PermissionError, LookupError):
                yield 'event: error\ndata: {"code":"access-expired"}\n\n'
                return
            for event in batch['events']:
                after = event['sequence']
                yield f'id: {after}\nevent: platform-event\ndata: {json.dumps(event)}\n\n'
            if batch['status'] in TERMINAL and len(batch['events']) < 100:
                return
            if not batch['events']:
                yield ': keep-alive\n\n'
            await asyncio.sleep(0.25)


def append_event(db, task_id, user_id, event, metadata):
    from .platform_repository import canonical
    if db.execute('SELECT COUNT(*) FROM platform_events WHERE task_id=?', (task_id,)).fetchone()[0] >= 128:
        raise ValueError('Task event budget exceeded')
    db.execute('INSERT INTO platform_events(task_id,user_id,event,metadata,created) VALUES (?,?,?,?,?)',
               (task_id, user_id, event, canonical(metadata, 2048), time.time()))
