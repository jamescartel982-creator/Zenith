import tempfile
import unittest
from uuid import uuid4
from unittest.mock import Mock
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.providers import trim_messages, OllamaProvider


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = Settings(data_dir=self.directory.name, api_token='a' * 40)
        self.provider = Mock()
        self.provider.generate.side_effect = lambda messages: ('Model answer', messages)
        self.agent = Agent(self.settings, self.provider)
        self.client = TestClient(create_app(self.settings, self.agent))
        self.headers = {'Authorization': 'Bearer ' + self.settings.api_token}
        self.session = str(uuid4())

    def chat(self, text='Hello', session=None):
        return self.client.post('/api/chat', json={'session_id': session or self.session, 'message': text}, headers=self.headers)

    def test_authentication_and_session_isolation(self):
        self.assertEqual(self.client.get('/healthz').status_code, 200)
        self.assertEqual(self.client.get('/api/history/' + self.session).status_code, 401)
        self.assertEqual(self.client.post('/api/chat', json={'session_id': self.session, 'message': 'Hello'}).status_code, 401)
        response = self.chat()
        self.assertEqual(response.status_code, 200)
        other = str(uuid4())
        self.assertEqual(self.client.get('/api/history/' + other, headers=self.headers).json()['turns'], [])
        result = self.client.post('/api/feedback', json={'session_id': other, 'turn_id': response.json()['id'], 'rating': 'good', 'approved': True}, headers=self.headers)
        self.assertEqual(result.status_code, 404)

    def test_real_message_roles_and_no_cross_session_context(self):
        self.chat('My name is Ada')
        self.chat('What is my name?')
        messages = self.provider.generate.call_args.args[0]
        self.assertEqual([m['role'] for m in messages], ['system', 'user', 'assistant', 'user'])
        self.assertEqual(messages[1]['content'], 'My name is Ada')
        self.chat('Different conversation', str(uuid4()))
        self.assertEqual(len(self.provider.generate.call_args.args[0]), 2)

    def test_errors_do_not_save_failed_turns_or_leak_internal_details(self):
        self.provider.generate.side_effect = RuntimeError('sensitive internal diagnostic')
        with self.assertLogs('zenith', level='ERROR'):
            response = self.chat()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('sensitive', response.text)
        self.assertEqual(self.agent.store.history(self.session), [])
        self.provider.generate.side_effect = lambda messages: ('', messages)
        with self.assertLogs('zenith', level='ERROR'):
            self.assertEqual(self.chat().status_code, 503)
        self.assertEqual(self.agent.store.history(self.session), [])

    def test_busy_requests_are_bounded_and_validation_rejects_empty(self):
        self.agent.lock.acquire()
        try:
            self.assertEqual(self.chat().status_code, 429)
        finally:
            self.agent.lock.release()
        self.assertEqual(self.chat('   ').status_code, 400)
        self.assertEqual(self.chat('x' * 12001).status_code, 422)

    def test_feedback_correction_and_deletion(self):
        turn = self.chat().json()
        payload = {'session_id': self.session, 'turn_id': turn['id'], 'rating': 'bad', 'approved': True}
        self.assertEqual(self.client.post('/api/feedback', json=payload, headers=self.headers).status_code, 400)
        payload['correction'] = 'Correct answer'
        self.assertEqual(self.client.post('/api/feedback', json=payload, headers=self.headers).status_code, 200)
        self.assertEqual(self.agent.store.approved_examples()[0]['messages'][-1]['content'], 'Correct answer')
        self.assertEqual(self.client.delete('/api/history/' + self.session, headers=self.headers).status_code, 200)
        self.assertEqual(self.agent.store.approved_examples(), [])

    def test_static_ui_and_security_headers(self):
        response = self.client.get('/')
        self.assertIn('Message Zenith', response.text)
        self.assertIn("script-src 'self'", response.headers['content-security-policy'])
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)


class ProviderTests(unittest.TestCase):
    def test_trimming_preserves_pairs_and_current_question(self):
        messages = [{'role': r, 'content': str(i)} for i, r in enumerate(['system', 'user', 'assistant', 'user', 'assistant', 'user'])]
        used = trim_messages(messages, lambda items: len(items) <= 4)
        self.assertEqual(used, [messages[0], *messages[3:]])
        self.assertEqual(len(messages), 6)
        with self.assertRaises(ValueError):
            trim_messages(messages, lambda _: False)

    def test_ollama_request_is_bounded_and_keeps_roles(self):
        from unittest.mock import patch
        settings = Settings(provider='ollama', max_new_tokens=23)
        messages = [{'role': 'system', 'content': 'System'}, {'role': 'user', 'content': 'Hello'}]
        with patch('agent.providers.requests.post') as post:
            post.return_value.json.return_value = {'message': {'content': 'Hi'}}
            result, used = OllamaProvider(settings).generate(messages)
        self.assertEqual(result, 'Hi')
        self.assertEqual(used, messages)
        self.assertEqual(post.call_args.kwargs['json']['options']['num_predict'], 23)
