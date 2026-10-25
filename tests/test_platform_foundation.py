"""Real SQLite, legacy-writer compatibility, auth revocation and audit integrity."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import pyotp

from agent.audit_chain import AuditChain
from agent.config import Settings
from agent.core import Agent
from agent.permissions import ActorContext, Permissions
from agent.platform_config import PlatformConfig
from agent.platform_migrations import migrate
from agent.platform_repository import backup, canonical
from agent.redaction import Redactor
from agent.storage import Store
from scripts.platform_protection import capture, compare, check_destination


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def test_additive_migration_is_atomic_idempotent_and_old_writers_work(self):
        with self.store.connect() as db:
            before = {r['name']: r['sql'] for r in db.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        migrate(self.store); migrate(self.store)
        with self.store.connect() as db:
            after = {r['name']: r['sql'] for r in db.execute('SELECT name,sql FROM sqlite_master')}
            self.assertEqual(db.execute('SELECT COUNT(*) FROM platform_schema_migrations').fetchone()[0], 1)
        for name, sql in before.items():
            self.assertEqual(after[name], sql)
        # Exercise current constructors and old positional writers after migration.
        agent = Agent(Settings(provider='ollama', data_dir=self.folder.name), provider=Mock(), store=self.store)
        user = agent.personal.register('alice', 'Alice', 'long fixture password')
        note = agent.personal.remember(user['id'], 'My telescope is violet')
        self.assertEqual(agent.personal.memories(user['id'])[0]['id'], note)
        self.store.add('legacy-session', 'hello', 'world', [], 'native')
        self.assertEqual(self.store.history('legacy-session')[0]['response'], 'world')

    def test_failed_migration_rolls_back_and_newer_schema_refuses_downgrade(self):
        with patch('agent.platform_migrations.SCHEMA', ('CREATE TABLE platform_partial(x)', 'INVALID SQL')):
            with self.assertRaises(sqlite3.Error):
                migrate(self.store)
        with self.store.connect() as db:
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='platform_partial'").fetchone())
        migrate(self.store)
        with self.store.connect() as db:
            db.execute('UPDATE platform_schema_migrations SET version=2')
        with self.assertRaises(ValueError):
            migrate(self.store)

    def test_backup_includes_wal_state_without_overwriting_source_or_destination(self):
        self.store.add('s', 'one', 'two', [], 'native')
        path = backup(self.store, Path(self.folder.name)/'backup.sqlite3')
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute('SELECT response FROM turns').fetchone()[0], 'two')
        with self.assertRaises(ValueError):
            backup(self.store, path)
        with self.assertRaises(ValueError):
            backup(self.store, self.store.path)

    def test_invalid_flags_and_quotas_fail_closed(self):
        for kwargs in [dict(tools_enabled=True), dict(enabled=True, tools_enabled=True),
                       dict(enabled=1), dict(max_pending=0), dict(task_seconds=True), dict(per_user_pending=33), dict(enabled=True,memory_enabled=True)]:
            with self.assertRaises(ValueError):
                PlatformConfig(**kwargs)
        with patch.dict(os.environ, {'ZENITH_PLATFORM_ENABLED': 'perhaps'}):
            with self.assertRaises(ValueError):
                PlatformConfig.from_env()
        self.assertFalse(PlatformConfig().enabled)

    def test_secret_redaction_and_rejection_are_not_silent_argument_changes(self):
        r = Redactor(['literal-canary-123456'])
        for text in ['literal-canary-123456', 'sk-'+'a'*32, 'hf_'+'a'*30,
                     'Bearer '+'a'*32, 'password=verylongpassword', 'zenith-admin-'+'a'*43, 'https://user:privatevalue@example.org']:
            self.assertNotEqual(r.text(text), text)
            with self.assertRaises(ValueError):
                r.require_clean(text)
        self.assertEqual(r.text('ordinary math'), 'ordinary math')
        with self.assertRaises(ValueError):
            canonical({'n': float('nan')})
        with self.assertRaises(ValueError):
            canonical({'s': 'large'}, 2)
        deep = {}; deep['nested'] = deep
        with self.assertRaises(ValueError):
            canonical(deep)

    def test_audit_chain_detects_tampering_and_external_anchor_detects_truncation(self):
        migrate(self.store); chain = AuditChain(self.store)
        first = chain.append('task-created', {'task_id': 'one'})
        anchor = chain.append('task-state', {'task_id': 'one', 'status': 'completed'})
        self.assertTrue(chain.verify(anchor)['valid'])
        with self.store.connect() as db:
            db.execute('DELETE FROM platform_audit WHERE sequence=2')
        self.assertTrue(chain.verify(first)['valid'])
        self.assertFalse(chain.verify(anchor)['valid'])
        with self.store.connect() as db:
            db.execute("UPDATE platform_audit SET metadata='{}' WHERE sequence=1")
        self.assertFalse(chain.verify()['valid'])
        with self.assertRaises(ValueError):
            AuditChain(self.store)

    def test_audit_concurrent_writers_and_missing_key_do_not_reset_history(self):
        migrate(self.store); chain = AuditChain(self.store)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: chain.append('task-created', {'task_id': str(i)}), range(12)))
        self.assertEqual(chain.verify()['sequence'], 12)
        with self.assertRaises(ValueError):
            chain.append('task-created', {'prompt': 'not audit metadata'})
        (Path(self.folder.name)/'platform-audit.key').unlink()
        with self.assertRaises(ValueError):
            AuditChain(self.store)
        self.assertFalse((Path(self.folder.name)/'platform-audit.key').exists())

    def test_protection_receipts_read_existing_files_and_ignore_code_commit_change(self):
        path = Path(self.folder.name)/'adapter'; path.mkdir()
        (path/'weights.bin').write_bytes(b'unchanged weights')
        settings = Settings(adapter=str(path))
        first = capture(settings)
        self.assertTrue(compare(first, dict(first, source_commit='future code commit')))
        (path/'weights.bin').write_bytes(b'changed')
        self.assertFalse(compare(first, capture(settings)))
        for output in (path/'new-receipt.json', path/'weights.bin'):
            with self.assertRaises(ValueError):check_destination(settings,Path(self.folder.name)/'profile.env',output)

    def test_protection_receipt_also_works_without_git_in_an_installed_environment(self):
        with patch('scripts.platform_protection.subprocess.run', side_effect=FileNotFoundError):
            receipt = capture(Settings(adapter=''))
        self.assertIsNone(receipt['source_commit'])
        self.assertEqual(receipt['adapter_files'], {})


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.agent = Agent(Settings(provider='ollama', data_dir=self.folder.name), provider=Mock())
        migrate(self.agent.store)
        self.config = PlatformConfig(enabled=True, runtime_enabled=True, tools_enabled=True)
        self.permissions = Permissions(self.agent.store, self.agent.personal, self.agent.execution, self.config)
        self.user = self.agent.personal.register('owner', 'Owner', 'long fixture password')
        self.token = self.agent.personal.issue_session(self.user['id'])
        self.actor = self.permissions.resolve(self.token)

    def activate_owner(self):
        path = Path(self.folder.name)/'fixture-owner.txt'
        self.agent.admin.initialize('owner', path)
        self.assertTrue(self.agent.admin.unlock(self.user['id'], self.token, path.read_text().strip()))
        seed = self.agent.admin.mfa.begin(self.user['id'], 'owner')['secret']
        self.assertTrue(self.agent.admin.mfa.verify(self.user['id'], self.token, pyotp.TOTP(seed).now(), enroll=True))
        self.agent.execution.grant(self.user['id'], self.token, 'sha256', {'kind': 'offline'})

    def test_owner_tools_require_actual_mfa_and_grant_and_live_session(self):
        with self.assertRaises(PermissionError):
            self.permissions.require_tool(self.actor, 'sha256')
        self.activate_owner()
        self.permissions.require_tool(self.actor, 'sha256')
        result = self.agent.execution.execute_session(self.actor.user_id, self.actor.session_hash, 'sha256', {'text': 'hello'})
        self.assertIn(hashlib.sha256(b'hello').hexdigest(), str(result))
        self.agent.personal.logout(self.token)
        with self.assertRaises(PermissionError):
            self.permissions.require_tool(self.actor, 'sha256')
        with self.assertRaises(PermissionError):
            self.agent.execution.execute_session(self.actor.user_id, self.actor.session_hash, 'sha256', {'text': 'hello'})

    def test_forged_user_revision_and_emergency_stop_fail_before_effect(self):
        self.activate_owner()
        for forged in [replace(self.actor, user_id='someone-else'), replace(self.actor, revision=99)]:
            with self.assertRaises(PermissionError):
                self.permissions.require_tool(forged, 'sha256')
        self.agent.execution.emergency(self.user['id'], self.token)
        with patch('agent.tools.run_tool') as effect:
            with self.assertRaises(PermissionError):
                self.agent.execution.execute_session(self.actor.user_id, self.actor.session_hash, 'sha256', {'text': 'hello'})
            effect.assert_not_called()

    def test_revision_revocation_and_disabled_flag_invalidate_effective_authority(self):
        self.activate_owner()
        disabled = Permissions(self.agent.store, self.agent.personal, self.agent.execution, PlatformConfig(enabled=True))
        with self.assertRaises(PermissionError):
            disabled.require_tool(self.actor, 'sha256')
        self.permissions.revoke(self.actor)
        with self.assertRaises(PermissionError):
            self.permissions.validate(self.actor)
        self.assertNotIn(self.token, repr(self.actor))


if __name__ == '__main__':
    unittest.main()
