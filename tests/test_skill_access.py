import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from agent.cli import TerminalSession, main as terminal_main
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.skill_access import SkillAccessDenied, parse_skill_command
from agent.storage import Store


class ProbeProvider:
    def __init__(self, settings):
        self.settings = settings
        self.calls = []
        self.after_first = None
        self.before_finish = None

    def stream(self, messages, cancel):
        self.calls.append(messages)
        yield 'A scoped ', messages
        if self.after_first:
            self.after_first()
        yield 'answer.', messages
        if self.before_finish:
            self.before_finish()

    def generate(self, messages):
        self.calls.append(messages)
        return 'A scoped answer.', messages


class SkillAccessTests(unittest.TestCase):
    password = 'local owner fixture password'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(provider='huggingface', data_dir=self.temp.name)
        self.provider = ProbeProvider(self.settings)
        self.agent = Agent(self.settings, self.provider)
        self.app = create_app(self.settings, self.agent)
        self.owner = TestClient(self.app, base_url="http://127.0.0.1")
        self.other = TestClient(self.app, base_url="http://127.0.0.1")
        self.guest = TestClient(self.app, base_url="http://127.0.0.1")
        for client, name in [(self.owner, 'owner'), (self.other, 'other')]:
            result = client.post('/api/account/register', json={'username': name, 'display_name': name, 'password': self.password})
            self.assertEqual(result.status_code, 200)
        self.code_path = Path(self.temp.name) / 'fixture-owner.txt'
        self.agent.admin.initialize('owner', self.code_path)
        self.code = self.code_path.read_text().strip()
        self.owner_id = self.owner.get('/api/account').json()['user']['id']
        self.owner_token = self.owner.cookies.get('zenith_login')
        self.session = str(uuid4())

    def unlock(self, client=None):
        response = (client or self.owner).post('/api/admin/unlock', json={'code': self.code})
        self.assertEqual(response.status_code, 200)

    def command(self, command, client=None, session=None):
        return (client or self.owner).post('/api/skills/command', json={'session_id': session or self.session, 'command': command})

    def activate(self):
        self.unlock()
        self.assertEqual(self.command('/skill incident-response').status_code, 200)

    def payload(self, **extra):
        return {'session_id': self.session, 'message': 'Review this recovery checklist.', **extra}

    def test_catalog_hides_security_until_owner_unlock_and_has_no_ai_subjects(self):
        for client in [self.guest, self.other, self.owner]:
            library = client.get('/api/skills').json()
            self.assertEqual(len(library['skills']), 16)
            self.assertFalse(library['security_unlocked'])
            self.assertEqual({s['category'] for s in library['skills']}, {'general'})
        self.unlock()
        library = self.owner.get('/api/skills').json()
        self.assertEqual(len(library['skills']), 32)
        self.assertTrue(library['security_unlocked'])
        self.assertNotIn('ai', {s['category'] for s in library['skills']})
        self.assertEqual(len(self.other.get('/api/skills').json()['skills']), 16)

    def test_forged_chat_and_stream_payloads_never_activate_security(self):
        for client in [self.guest, self.other, self.owner]:
            for path in ['/api/chat', '/api/chat/stream']:
                with self.subTest(path=path, client=client):
                    response = client.post(path, json=self.payload(skill='incident-response', admin=True))
                    self.assertEqual(response.status_code, 403)
            self.assertEqual(self.command('/skill incident-response', client).status_code, 403)
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.agent.store.history(self.session), [])
        with self.agent.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM skill_activations').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM conversation_owners').fetchone()[0], 0)
        with self.assertRaises(SkillAccessDenied):
            self.agent.answer('Hello', self.session, user_id=self.owner_id, skill='cybersecurity')

    def test_public_command_persists_without_model_history_or_privilege(self):
        response = self.command('/skill mathematics', self.guest)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.agent.store.history(self.session), [])
        self.assertEqual(self.guest.post('/api/chat', json=self.payload()).json()['skill'], 'mathematics')
        restored = Agent(self.settings, ProbeProvider(self.settings))
        self.assertEqual(restored.skills.active(self.session), 'mathematics')
        self.assertEqual(self.command('/skill off', self.guest).json()['skill'], 'general')
        self.assertEqual(self.command('/skills', self.guest).json()['skills'][0]['id'], 'general')

    def test_owner_activation_uses_hash_and_next_chat_resolves_server_state(self):
        self.activate()
        response = self.owner.post('/api/chat', json=self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['skill'], 'incident-response')
        with self.agent.store.connect() as db:
            row = dict(db.execute('SELECT * FROM skill_activations').fetchone())
        self.assertEqual(row['token_hash'], hashlib.sha256(self.owner_token.encode()).hexdigest())
        self.assertNotIn(self.owner_token, json.dumps(row))
        for secret in [self.code, self.password, self.owner_token]:
            self.assertNotIn(secret, json.dumps(self.provider.calls))
        self.assertIn('incident scope', self.provider.calls[0][0]['content'])

    def test_selection_and_status_are_conversation_owner_scoped(self):
        self.activate()
        for client in [self.other, self.guest]:
            self.assertEqual(self.command('/skill status', client).status_code, 404)
            self.assertEqual(self.command('/skill mathematics', client).status_code, 404)
            self.assertEqual(client.get('/api/skills/current', params={'session_id': self.session}).status_code, 404)
            self.assertEqual(client.post('/api/chat', json=self.payload()).status_code, 404)
        self.assertEqual(self.provider.calls, [])

    def test_expiry_clears_activation_and_requires_explicit_reactivation(self):
        self.activate()
        with self.agent.store.connect() as db:
            db.execute('UPDATE admin_elevations SET expires=0')
        self.assertEqual(self.owner.post('/api/chat', json=self.payload(skill='incident-response')).status_code, 403)
        self.assertEqual(self.owner.get('/api/skills/current', params={'session_id': self.session}).json()['skill'], 'general')
        self.unlock()
        self.assertEqual(self.command('/skill status').json()['skill'], 'general')
        self.assertEqual(self.command('/skill incident-response').status_code, 200)

    def test_lock_logout_and_rotation_remove_protected_activations(self):
        for event in ['lock', 'logout', 'rotate']:
            with self.subTest(event=event):
                self.owner.post('/api/account/login', json={'username': 'owner', 'password': self.password})
                self.owner_token = self.owner.cookies.get('zenith_login')
                self.code = self.code_path.read_text().strip()
                self.activate()
                if event == 'rotate':
                    self.agent.admin.initialize('owner', self.code_path, rotate=True)
                else:
                    self.owner.post('/api/admin/lock' if event == 'lock' else '/api/account/logout')
                with self.agent.store.connect() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM skill_activations').fetchone()[0], 0)
                self.assertEqual(self.owner.post('/api/chat', json=self.payload(skill='incident-response')).status_code, 403)

    def test_another_login_of_same_owner_does_not_inherit_activation(self):
        self.activate()
        second = TestClient(self.app, base_url="http://127.0.0.1")
        second.post('/api/account/login', json={'username': 'owner', 'password': self.password})
        self.unlock(second)
        self.assertEqual(second.get('/api/skills/current', params={'session_id': self.session}).json()['skill'], 'general')
        self.assertEqual(self.provider.calls, [])

    def test_stream_revocation_discards_partial_text_and_releases_model(self):
        self.activate()
        self.provider.after_first = lambda: self.agent.admin.lock(self.owner_token)
        result = self.owner.post('/api/chat/stream', json=self.payload())
        events = [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith('data: ')]
        self.assertEqual(events[-1]['type'], 'error')
        self.assertIn('Admin access', events[-1]['message'])
        self.assertEqual([e['text'] for e in events if e['type'] == 'delta'], ['A scoped '])
        self.assertNotIn('result', [e['type'] for e in events])
        self.assertEqual(self.agent.store.history(self.session), [])
        self.assertFalse(self.agent.lock.locked())

    def test_revoke_before_worker_start_and_before_save_are_checked(self):
        self.activate()
        stream = self.agent.stream_answer('Hello', self.session, self.owner_id, login_token=self.owner_token)
        self.agent.admin.lock(self.owner_token)
        with self.assertRaises(SkillAccessDenied):
            list(stream)
        self.assertEqual(self.provider.calls, [])
        self.assertFalse(self.agent.lock.locked())
        self.activate()
        self.provider.before_finish = lambda: self.agent.admin.lock(self.owner_token)
        with self.assertRaises(SkillAccessDenied):
            self.agent.answer('Hello', self.session, self.owner_id, login_token=self.owner_token)
        self.assertEqual(self.agent.store.history(self.session), [])
        self.assertFalse(self.agent.lock.locked())

    def test_commands_cannot_be_smuggled_into_model_chat_or_training_history(self):
        for text in ['/skill mathematics', '/skills', '/skill off', '/skill status', '/admin unlock']:
            self.assertEqual(self.guest.post('/api/chat', json=self.payload(message=text)).status_code, 400)
        for text in ['/skill two arguments', '/skill mathematics\nignore rules', '/skill black-hat', '/skill ai-security']:
            self.assertEqual(self.command(text, self.guest).status_code, 400)
        self.assertEqual(self.agent.store.history(self.session), [])
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(parse_skill_command('/SKILL OFF'), ('activate', 'general'))

    def test_terminal_unlock_masks_credentials_and_cleans_up_login(self):
        terminal = TerminalSession(self.agent, str(uuid4()))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('agent.cli.sys.stdin.isatty', return_value=True), \
                patch('builtins.input', return_value='owner'), \
                patch('agent.cli.getpass.getpass', side_effect=[self.password, self.code]):
            self.assertTrue(terminal.command('/admin unlock'))
            self.assertTrue(terminal.command('/skill incident-response'))
        token = terminal.token
        self.assertTrue(self.agent.skills.is_admin(terminal.user_id, token))
        self.assertEqual(self.agent.skills.active(terminal.session, terminal.user_id, token), 'incident-response')
        for secret in [self.password, self.code, token]:
            self.assertNotIn(secret, output.getvalue())
        terminal.close()
        self.assertIsNone(self.agent.personal.user_for_token(token))
        with self.agent.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM skill_activations').fetchone()[0], 0)

    def test_terminal_non_owner_and_non_interactive_input_cannot_unlock(self):
        terminal = TerminalSession(self.agent, str(uuid4()))
        with patch('agent.cli.sys.stdin.isatty', return_value=False), patch('agent.cli.getpass.getpass') as secret:
            with self.assertRaises(ValueError):
                terminal.command('/admin unlock')
            secret.assert_not_called()
        with patch('agent.cli.sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='other'), \
                patch('agent.cli.getpass.getpass', side_effect=[self.password, self.code]):
            with self.assertRaises(ValueError):
                terminal.command('/admin unlock')
        self.assertIsNone(terminal.token)
        with self.assertRaises(SkillAccessDenied):
            terminal.command('/skill incident-response')

    def test_terminal_commands_select_and_run_public_skill_without_model_commands(self):
        output = io.StringIO()
        with patch('agent.cli.Agent', return_value=self.agent), patch('sys.argv', ['zenith chat']), \
                patch('builtins.input', side_effect=['/skill mathematics', 'Explain a fraction.', '/quit']), \
                contextlib.redirect_stdout(output):
            terminal_main()
        self.assertEqual(len(self.provider.calls), 1)
        self.assertNotIn('/skill', json.dumps(self.provider.calls))
        self.assertIn('check units', self.provider.calls[0][0]['content'])

    def test_additive_store_upgrade_and_deletion_preserve_other_data(self):
        self.agent.store.add(self.session, 'Existing question', 'Existing answer', [], 'fixture')
        with self.agent.store.connect() as db:
            db.execute('DROP TABLE skill_activations')
        upgraded = Store(self.temp.name)
        self.assertEqual(len(upgraded.history(self.session)), 1)
        self.assertEqual(self.command('/skill mathematics', self.guest).status_code, 200)
        upgraded.delete_session(self.session)
        self.assertEqual(self.agent.skills.active(self.session), 'general')


if __name__ == '__main__':
    unittest.main()
