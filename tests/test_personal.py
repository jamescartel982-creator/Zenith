import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.personal import PersonalStore


class PersonalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.provider = Mock(); self.provider.generate.side_effect = lambda messages: ('A useful answer', messages)
        self.settings = Settings(provider='huggingface', data_dir=self.folder.name)
        self.agent = Agent(self.settings, self.provider)
        self.app = create_app(self.settings, self.agent)
        self.alice = TestClient(self.app); self.bob = TestClient(self.app)
        self.password = 'a long testing password'

    def register(self, client, username='alice', name='Alice'):
        result = client.post('/api/account/register', json={'username': username, 'display_name': name, 'password': self.password})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['user']

    def chat(self, client, session=None, message='Hello'):
        return client.post('/api/chat', json={'session_id': session or str(uuid4()), 'message': message})

    def test_password_storage_cookie_logout_and_welcome_back(self):
        user = self.register(self.alice)
        cookie = self.alice.cookies.get('zenith_login')
        self.assertIn('Welcome back, Alice', self.alice.get('/api/account').json()['greeting'])
        with self.agent.store.connect() as db:
            row = db.execute('SELECT * FROM users').fetchone()
            self.assertNotEqual(row['password_hash'], self.password)
            self.assertNotEqual(row['password_hash'], hashlib.sha256(self.password.encode()).hexdigest())
            self.assertNotEqual(db.execute('SELECT token_hash FROM login_sessions').fetchone()[0], cookie)
        self.assertEqual(self.alice.post('/api/account/logout').status_code, 200)
        self.assertIsNone(self.alice.get('/api/account').json()['user'])
        self.assertIsNone(self.agent.personal.user_for_token(cookie))
        result = self.alice.post('/api/account/login', json={'username': 'ALICE', 'password': self.password})
        self.assertEqual(result.status_code, 200)
        self.assertIn('httponly', result.headers['set-cookie'].lower())
        self.assertIn('samesite=strict', result.headers['set-cookie'].lower())
        self.assertEqual(result.json()['user']['id'], user['id'])
        previous_cookie = self.alice.cookies.get('zenith_login')
        self.register(self.alice, 'bobby', 'Bob')
        self.assertIsNone(self.agent.personal.user_for_token(previous_cookie))

    def test_wrong_password_expiry_and_cross_site_requests_are_rejected(self):
        self.register(self.alice)
        result = self.bob.post('/api/account/login', json={'username': 'alice', 'password': 'incorrect'})
        self.assertEqual(result.status_code, 401)
        token = self.alice.cookies.get('zenith_login')
        with self.agent.store.connect() as db:
            db.execute('UPDATE login_sessions SET expires=?', (time.time()-1,))
        self.assertIsNone(self.agent.personal.user_for_token(token))
        self.assertEqual(self.alice.post('/api/account/logout', headers={'Origin': 'https://unrelated.example'}).status_code, 403)

    def test_accounts_require_existing_server_access_when_configured(self):
        settings = Settings(provider='huggingface', data_dir=self.folder.name, api_token='a'*40)
        client = TestClient(create_app(settings, self.agent))
        payload = {'username': 'alice', 'display_name': 'Alice', 'password': self.password}
        self.assertEqual(client.post('/api/account/register', json=payload).status_code, 401)
        self.assertEqual(client.get('/api/model-packs').status_code, 401)
        self.assertEqual(client.post('/api/account/register', json=payload, headers={'Authorization': 'Bearer '+'a'*40}).status_code, 200)

    def test_login_attempts_are_bounded(self):
        for _ in range(8):
            self.assertEqual(self.alice.post('/api/account/login', json={'username': 'nobody', 'password': self.password}).status_code, 401)
        self.assertEqual(self.alice.post('/api/account/login', json={'username': 'nobody', 'password': self.password}).status_code, 429)

    def test_validation_and_case_insensitive_unique_usernames(self):
        for username, name, password in [('x', 'Name', self.password), ('valid', '', self.password), ('valid', 'Name', 'short')]:
            with self.assertRaises(ValueError): self.agent.personal.register(username, name, password)
        self.register(self.alice)
        with self.assertRaises(ValueError): self.agent.personal.register('ALICE', 'Other', self.password)

    def test_memories_are_private_persistent_explicit_and_deletable(self):
        alice = self.register(self.alice)
        self.register(self.bob, 'bobby', 'Bob')
        self.assertEqual(TestClient(self.app).get('/api/memories').status_code, 401)
        result = self.alice.post('/api/memories', json={'content': 'My project is a violet telescope.'})
        identifier = result.json()['id']
        self.assertEqual(self.bob.get('/api/memories').json()['memories'], [])
        self.assertEqual(self.bob.delete('/api/memories/'+identifier).status_code, 404)
        self.assertEqual(len(PersonalStore(self.agent.store).memories(alice['id'])), 1)
        self.chat(self.alice, message='What is my project?')
        self.assertIn('violet telescope', self.provider.generate.call_args.args[0][0]['content'])
        self.chat(self.bob, message='What is my project?')
        self.assertNotIn('violet telescope', self.provider.generate.call_args.args[0][0]['content'])
        self.assertEqual(self.agent.store.approved_examples(), [])
        self.assertEqual(self.alice.delete('/api/memories/'+identifier).status_code, 200)
        self.chat(self.alice, message='What is my project?')
        self.assertNotIn('violet telescope', self.provider.generate.call_args.args[0][0]['content'])

    def test_conversation_history_feedback_and_deletion_require_ownership(self):
        self.register(self.alice); self.register(self.bob, 'bobby', 'Bob')
        session = str(uuid4()); turn = self.chat(self.alice, session).json()
        strangers = [self.bob, TestClient(self.app)]
        for client in strangers:
            self.assertEqual(client.get('/api/history/'+session).status_code, 404)
            self.assertEqual(client.delete('/api/history/'+session).status_code, 404)
            self.assertEqual(self.chat(client, session).status_code, 404)
            self.assertEqual(client.post('/api/feedback', json={'session_id': session, 'turn_id': turn['id'], 'rating': 'good'}).status_code, 404)
        self.assertEqual(self.alice.get('/api/conversations').json()['conversations'][0]['session_id'], session)
        self.assertEqual(self.bob.get('/api/conversations').json()['conversations'], [])
        self.assertEqual(self.alice.delete('/api/history/'+session).status_code, 200)
        self.assertEqual(self.alice.get('/api/conversations').json()['conversations'], [])

    def test_existing_anonymous_conversations_cannot_be_claimed_by_login(self):
        session = str(uuid4()); self.chat(self.bob, session)
        self.register(self.alice)
        self.assertEqual(self.alice.get('/api/history/'+session).status_code, 404)
        self.assertEqual(self.bob.get('/api/history/'+session).status_code, 200)

    def test_memory_limits_and_context_budget(self):
        user = self.register(self.alice)
        for i in range(50): self.agent.personal.remember(user['id'], f'Preference {i}: '+ 'x'*450)
        with self.assertRaises(ValueError): self.agent.personal.remember(user['id'], 'one too many')
        selected = self.agent.personal.context_memories(user['id'], 'Preference', 1024)
        self.assertLessEqual(sum(len(note['content']) for note in selected), 1024)
        self.assertLessEqual(len(selected), 8)
        self.assertEqual(self.alice.delete('/api/memories').json()['deleted'], 50)
