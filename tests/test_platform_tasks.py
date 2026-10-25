"""Durable task ownership, lease fencing, exact approval and event replay."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import pyotp

from agent.approvals import Approvals
from agent.audit_chain import AuditChain
from agent.config import Settings
from agent.core import Agent
from agent.event_bus import EventBus
from agent.permissions import Permissions
from agent.platform_config import PlatformConfig
from agent.platform_migrations import migrate
from agent.task_store import CapacityError, LeaseLost, TaskStore


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.agent = Agent(Settings(provider='ollama', data_dir=self.folder.name), provider=Mock())
        self.store = self.agent.store; migrate(self.store)
        self.config = PlatformConfig(enabled=True, runtime_enabled=True, tools_enabled=True)
        self.permissions = Permissions(self.store, self.agent.personal, self.agent.execution, self.config)
        self.user = self.agent.personal.register('alice', 'Alice', 'long fixture password')
        self.token = self.agent.personal.issue_session(self.user['id'])
        self.actor = self.permissions.resolve(self.token)
        other = self.agent.personal.register('bobby', 'Bob', 'long fixture password')
        self.other = self.permissions.resolve(self.agent.personal.issue_session(other['id']))
        self.audit = AuditChain(self.store)
        self.tasks = TaskStore(self.store, self.permissions, self.audit, self.config)
        self.events = EventBus(self.store, self.permissions)
        self.approvals = Approvals(self.tasks, self.permissions, self.audit)

    def grant(self):
        path = Path(self.folder.name)/'fixture-code'
        self.agent.admin.initialize('alice', path)
        self.agent.admin.unlock(self.user['id'], self.token, path.read_text().strip())
        seed = self.agent.admin.mfa.begin(self.user['id'], 'alice')['secret']
        self.agent.admin.mfa.verify(self.user['id'], self.token, pyotp.TOTP(seed).now(), enroll=True)
        self.agent.execution.grant(self.user['id'], self.token, 'tcp-connect', {
            'kind': 'network', 'cidrs': ['127.0.0.1/32'], 'ports': [443],
            'authorization_reference': 'Owned loopback test fixture'})

    def create(self):
        return self.tasks.create(self.actor, 'diagnostics', {'steps': []})['id']

    def test_task_creation_and_events_are_atomic_and_account_scoped(self):
        identifier = self.create()
        self.assertEqual(self.tasks.get(self.actor, identifier)['status'], 'queued')
        for action in [lambda: self.tasks.get(self.other, identifier), lambda: self.events.read(self.other, identifier),
                       lambda: self.tasks.cancel(self.other, identifier)]:
            with self.assertRaises(LookupError): action()
        batch = self.events.read(self.actor, identifier)
        self.assertEqual(len(batch['events']), 1)
        self.assertEqual(self.events.read(self.actor, identifier, batch['events'][0]['sequence'])['events'], [])
        self.assertNotIn('session_hash', json.dumps(self.tasks.get(self.actor, identifier)))
        with patch.object(self.audit, 'append', side_effect=OSError('full disk')):
            with self.assertRaises(OSError): self.create()
        self.assertEqual(len(self.tasks.list(self.actor)), 1)

    def test_capacity_is_checked_transactionally(self):
        for _ in range(self.config.per_user_pending): self.create()
        with self.assertRaises(CapacityError): self.create()
        self.tasks.cancel(self.actor, self.tasks.list(self.actor)[0]['id'])
        self.create()

    def test_lease_heartbeat_old_worker_fenced_and_crash_never_blindly_replays(self):
        identifier = self.create()
        self.assertEqual(self.tasks.claim('worker-one')['id'], identifier)
        self.assertIsNone(self.tasks.claim('worker-two'))
        self.assertTrue(self.tasks.heartbeat(identifier, 'worker-one'))
        self.assertFalse(self.tasks.heartbeat(identifier, 'worker-two'))
        with self.store.connect() as db:
            db.execute('UPDATE platform_tasks SET lease_until=? WHERE id=?', (time.time()-1, identifier))
        self.assertEqual(self.tasks.recover(), 1)
        self.assertEqual(self.tasks.get(self.actor, identifier)['status'], 'needs_reconciliation')
        with self.assertRaises(LeaseLost):
            self.tasks.finish(identifier, 'worker-one', 'completed', result={'should': 'not happen'})
        self.assertIsNone(self.tasks.claim('worker-two'))

    def test_cancellation_fences_effects_and_completed_task_cannot_be_resurrected(self):
        identifier = self.create(); self.tasks.claim('one')
        self.tasks.cancel(self.actor, identifier)
        self.assertFalse(self.tasks.heartbeat(identifier, 'one'))
        with self.store.connect() as db:
            with self.assertRaises(LeaseLost): self.tasks.fenced(db, identifier, 'one')
        self.tasks.finish(identifier, 'one', 'completed', result={'discarded': True})
        task = self.tasks.get(self.actor, identifier)
        self.assertEqual(task['status'], 'cancelled'); self.assertIsNone(task['result'])
        self.tasks.cancel(self.actor, identifier)
        self.assertEqual(self.tasks.get(self.actor, identifier)['status'], 'cancelled')

    def test_expired_session_prevents_queued_task_admission_to_worker(self):
        identifier = self.create()
        self.agent.personal.logout(self.token)
        self.assertIsNone(self.tasks.claim('worker'))
        self.assertEqual(self.tasks.internal(identifier)['error'], 'authorization-expired')

    def test_exact_approval_replay_argument_swap_and_cross_account_are_rejected(self):
        self.grant(); identifier = self.create(); self.tasks.claim('worker')
        arguments = {'host': '127.0.0.1', 'port': 443}
        self.assertFalse(self.approvals.prepare(self.actor, identifier, 'worker', 0, 'tcp-connect', arguments))
        approval = self.approvals.list(self.actor, identifier)[0]
        with self.assertRaises((PermissionError, LookupError)):
            self.approvals.decide(self.other, approval['id'], True)
        self.approvals.decide(self.actor, approval['id'], True)
        self.tasks.claim('worker')
        with self.assertRaises(PermissionError):
            self.approvals.prepare(self.actor, identifier, 'worker', 0, 'tcp-connect', {'host': '127.0.0.2', 'port': 443})
        self.assertTrue(self.approvals.prepare(self.actor, identifier, 'worker', 0, 'tcp-connect', arguments))
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.approvals.consume(db, self.actor, identifier, 0, 'tcp-connect', arguments)
        with self.store.connect() as db:
            with self.assertRaises(PermissionError):
                self.approvals.consume(db, self.actor, identifier, 0, 'tcp-connect', arguments)

    def test_revocation_after_approval_blocks_consumption_and_no_secrets_in_audit(self):
        self.grant(); identifier = self.create(); self.tasks.claim('worker')
        args = {'host': '127.0.0.1', 'port': 443}
        self.approvals.prepare(self.actor, identifier, 'worker', 0, 'tcp-connect', args)
        approval = self.approvals.list(self.actor, identifier)[0]
        self.approvals.decide(self.actor, approval['id'], True)
        self.agent.execution.revoke(self.user['id'], self.token)
        with self.store.connect() as db:
            with self.assertRaises(PermissionError):
                self.approvals.consume(db, self.actor, identifier, 0, 'tcp-connect', args)
            log = ' '.join(r['metadata'] for r in db.execute('SELECT metadata FROM platform_audit'))
            self.assertNotIn(self.token, log)
            self.assertNotIn('127.0.0.1', log)
        self.assertTrue(self.audit.verify()['valid'])


if __name__ == '__main__': unittest.main()
