"""Token-free guest/account chat with unchanged private-host and owner boundaries."""
from dataclasses import replace
import secrets
import tempfile
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.public_chat import COOKIE, LIFETIME, ChatLimiter, identity, issue


class PublicChatTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.key = secrets.token_urlsafe(32)
        self.settings = replace(Settings(), provider='huggingface', data_dir=folder.name,
                                api_token=self.key, public_chat=True)
        provider = Mock(); provider.generate.side_effect = lambda messages: ('Fixture answer.', messages)
        self.agent = Agent(self.settings, provider)
        self.app = create_app(self.settings, self.agent)
        self.client = self.browser()

    def browser(self):
        return TestClient(self.app, base_url='https://127.0.0.1')

    def bootstrap(self, client):
        result = client.get('/api/account'); self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.json()['user'])
        self.assertNotIn(self.key, result.text)
        return result

    def test_guest_cookie_is_separate_expiring_and_unforgeable(self):
        cookie = issue(self.key, now=1000)
        self.assertTrue(identity(cookie, self.key, now=1001).startswith('guest:'))
        self.assertIsNone(identity(cookie, self.key, now=1000 + LIFETIME))
        self.assertIsNone(identity(cookie, self.key, now=999))
        self.assertIsNone(identity(cookie, self.key + 'changed', now=1001))
        self.assertIsNone(identity(cookie[:-1] + 'z', self.key, now=1001))
        from agent.browser_access import valid
        self.assertFalse(valid(cookie, self.key, now=1001))

    def test_fresh_page_and_api_bootstrap_need_no_shared_secret(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        for flag in ('HttpOnly', 'Secure', 'SameSite=strict', 'Path=/'):
            self.assertIn(flag, page.headers['set-cookie'])
        self.assertNotIn('Domain=', page.headers['set-cookie'])
        self.assertNotIn(self.key, page.text + page.headers['set-cookie'])
        self.bootstrap(self.client)
        health = self.client.get('/healthz').json()
        self.assertTrue(health['public_chat']); self.assertFalse(health['authentication_required'])
        for path in ('/api/team', '/api/knowledge', '/api/skills', '/api/model-packs'):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_guest_history_skills_and_streams_are_browser_isolated(self):
        self.bootstrap(self.client); other = self.browser(); self.bootstrap(other)
        session = str(uuid4())
        result = self.client.post('/api/chat/stream', json={'session_id':session,'message':'Explain the supplied example.'})
        self.assertEqual(result.status_code, 200); self.assertIn('Fixture answer.', result.text)
        self.assertEqual(self.client.get('/api/history/' + session).status_code, 200)
        self.assertEqual(other.get('/api/history/' + session).status_code, 404)
        self.assertEqual(other.delete('/api/history/' + session).status_code, 404)
        self.assertEqual(other.post('/api/chat', json={'session_id':session,'message':'Read the previous answer.'}).status_code, 404)
        command = {'session_id':session, 'command':'/skill off'}
        self.assertEqual(other.post('/api/skills/command', json=command).status_code, 404)
        self.assertEqual(self.client.post('/api/skills/command', json=command).status_code, 200)
        # Existing legacy anonymous conversations cannot be claimed by a guest.
        legacy = str(uuid4()); self.agent.store.add(legacy, 'Private legacy prompt', 'Legacy answer', [], 'fixture')
        self.assertEqual(self.client.get('/api/history/' + legacy).status_code, 404)
        self.assertEqual(self.client.delete('/api/history/' + session).status_code, 200)

    def test_guest_cannot_become_account_owner_or_use_restricted_workflows(self):
        self.bootstrap(self.client)
        for path in ('/api/memories', '/api/conversations', '/api/admin/help',
                     '/api/admin/execution', '/api/admin/status', '/api/skills/search'):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        session = str(uuid4())
        from agent.skills import list_skills
        restricted = next(row['id'] for row in list_skills(include_admin=True) if row['access'] == 'admin')
        result = self.client.post('/api/chat', json={'session_id':session,'message':'Explain scope.','skill':restricted})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(self.client.post('/api/admin/unlock', json={'code':'forged','otp':'123456'}).status_code, 401)
        # Guest grants never satisfy the private host's API credential check.
        self.assertEqual(self.client.get('/api/team', headers={'Authorization':'Bearer wrong'}).status_code, 401)

    def test_accounts_login_without_server_token_and_keep_memories_private(self):
        self.bootstrap(self.client)
        result = self.client.post('/api/account/register', json={'username':'alice','display_name':'Alice',
                                  'password':'a temporary isolated password'})
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(COOKIE, self.client.cookies)
        self.assertEqual(self.client.post('/api/memories', json={'content':'My private preference.'}).status_code, 200)
        private_session = str(uuid4())
        self.assertEqual(self.client.post('/api/chat', json={'session_id':private_session,'message':'Private account example.'}).status_code, 200)
        self.assertEqual(self.client.get('/api/admin/help').status_code, 403)
        self.assertEqual(self.client.post('/api/account/logout').status_code, 200)
        self.assertIn(COOKIE, self.client.cookies)
        self.assertEqual(self.client.get('/api/memories').status_code, 401)
        self.assertEqual(self.client.get('/api/history/' + private_session).status_code, 404)
        self.assertEqual(self.client.post('/api/account/login', json={'username':'alice',
                                         'password':'a temporary isolated password'}).status_code, 200)
        self.assertIn('My private preference.', self.client.get('/api/memories').text)

    def test_public_chat_limits_and_csrf_hold_before_inference(self):
        self.bootstrap(self.client)
        self.assertEqual(self.client.post('/api/chat', headers={'Origin':'https://foreign.example'},
                         json={'session_id':str(uuid4()),'message':'Test'}).status_code, 403)
        # A direct verified arithmetic path avoids repeated fixture generation.
        for _ in range(20):
            self.assertEqual(self.client.post('/api/chat', json={'session_id':str(uuid4()),'message':'2+2'}).status_code, 200)
        self.assertEqual(self.client.post('/api/chat', json={'session_id':str(uuid4()),'message':'2+2'}).status_code, 429)
        limiter = ChatLimiter()
        self.assertTrue(all(limiter.admit('one', now=100) for _ in range(20)))
        self.assertFalse(limiter.admit('one', now=100)); self.assertTrue(limiter.admit('two', now=100))
        self.assertTrue(limiter.admit('one', now=160))

    def test_private_mode_preserves_token_requirement_and_native_bearer(self):
        private = create_app(replace(self.settings, public_chat=False), self.agent)
        client = TestClient(private, base_url='https://127.0.0.1')
        client.get('/')
        self.assertNotIn(COOKIE, client.cookies)
        self.assertEqual(client.get('/api/account').status_code, 401)
        self.assertEqual(client.get('/api/account', headers={'Authorization':'Bearer '+self.key}).status_code, 200)
        with self.assertRaises(ValueError):replace(self.settings, api_token='')


if __name__ == '__main__': unittest.main()
