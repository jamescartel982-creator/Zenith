"""Protocol failures must not become completed answers or training examples."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from agent.config import Settings
from agent.core import Agent
from agent.providers import LocalServerProvider, OllamaProvider
from agent.server import create_app
from agent.transport import ProviderProtocolError, ndjson_objects, sse_payloads


MESSAGES = [{'role': 'system', 'content': 'You are Zenith.'},
            {'role': 'user', 'content': 'Describe an apple.'}]


def response_bytes(*chunks):
    response = Mock()
    response.is_redirect = False
    response.iter_content.return_value = iter(chunks)
    return response


def sse(value):
    return ('data: ' + json.dumps(value, ensure_ascii=False) + '\n\n').encode()


class TransportTests(unittest.TestCase):
    def test_sse_unicode_crlf_comments_and_multiline_data(self):
        body = ('\ufeff: heartbeat\r\nid: 42\r\nevent: message\r\n'
                'data: {"choices":\r\ndata: [{"delta":{"content":"こんにちは"}}]}\r\n\r\n').encode()
        response = response_bytes(*(body[i:i + 1] for i in range(len(body))))
        values = list(sse_payloads(response, Event()))
        self.assertEqual(json.loads(values[0])['choices'][0]['delta']['content'], 'こんにちは')
        self.assertEqual(len(values), 1)

    def test_ndjson_handles_split_lines_and_rejects_malformed_objects(self):
        body = b'\n{"message":{"content":"Hello"}}\r\n{"done":true}'
        self.assertEqual(len(list(ndjson_objects(response_bytes(body[:9], body[9:]), Event()))), 2)
        for bad in [b'[]\n', b'null\n', b'{bad}\n', b'\xff\n', b'{"error":"private upstream detail"}\n']:
            with self.subTest(bad=bad), self.assertRaises(ProviderProtocolError) as failure:
                list(ndjson_objects(response_bytes(bad), Event()))
            self.assertNotIn('private upstream detail', str(failure.exception))

    def test_frames_stream_and_unterminated_events_are_bounded(self):
        with patch('agent.transport.MAX_FRAME_BYTES', 24):
            for body in [b'x' * 25, b'data: 1234567890\ndata: 1234567890\ndata: 1234567890\n\n']:
                with self.subTest(body=body), self.assertRaises(ProviderProtocolError):
                    list(sse_payloads(response_bytes(body), Event()))
        with patch('agent.transport.MAX_STREAM_BYTES', 10), self.assertRaises(ProviderProtocolError):
            list(sse_payloads(response_bytes(b': ping\n' * 3), Event()))
        with self.assertRaises(ProviderProtocolError):
            list(sse_payloads(response_bytes(b'data: [DONE]\n'), Event()))


class RemoteProviderTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(provider='localserver')

    def test_local_stream_completion_usage_and_no_credential_header(self):
        response = response_bytes(
            sse({'choices': [{'delta': {'content': 'Hello '}}]}),
            sse({'choices': [{'delta': {'content': '世界'}, 'finish_reason': 'length'}]}),
            sse({'choices': [], 'usage': {'prompt_tokens': 9, 'completion_tokens': 3}}),
            b'data: [DONE]\n\n')
        provider = LocalServerProvider(self.settings)
        with patch('agent.providers.requests.post', return_value=response) as post:
            text = ''.join(chunk for chunk, _ in provider.stream(MESSAGES, Event()))
        self.assertEqual(text, 'Hello 世界')
        self.assertEqual(provider.last_usage['total_tokens'], 12)
        self.assertEqual(provider.last_usage['finish_reason'], 'length')
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertNotIn('headers', post.call_args.kwargs)
        response.close.assert_called_once()

    def test_local_stream_requires_completion_and_rejects_invalid_events(self):
        first = sse({'choices': [{'delta': {'content': 'Partial'}}]})
        for tail in [b'', b'data: [DONE]\n', sse([]), sse({'choices': {}}),
                     sse({'choices': [{'delta': {'content': ['invalid']}}]}),
                     sse({'choices': [{'delta': {}, 'finish_reason': 'tool_calls'}]}),
                     sse({'error': 'private upstream detail'}), sse({'usage': 'invalid'})]:
            with self.subTest(tail=tail):
                response = response_bytes(first, tail)
                provider = LocalServerProvider(self.settings)
                with patch('agent.providers.requests.post', return_value=response):
                    with self.assertRaises(ProviderProtocolError) as failure:
                        list(provider.stream(MESSAGES, Event()))
                self.assertNotIn('private upstream detail', str(failure.exception))
                self.assertIsNone(provider.last_usage)
                response.close.assert_called_once()

    def test_explicit_finish_can_complete_without_done_and_late_text_fails(self):
        finish = sse({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})
        text = sse({'choices': [{'delta': {'content': 'Answer'}}]})
        provider = LocalServerProvider(self.settings)
        with patch('agent.providers.requests.post', return_value=response_bytes(text, finish)):
            self.assertEqual(list(provider.stream(MESSAGES, Event()))[0][0], 'Answer')
        with patch('agent.providers.requests.post', return_value=response_bytes(text, finish, text)):
            with self.assertRaises(ProviderProtocolError):
                list(provider.stream(MESSAGES, Event()))
        self.assertIsNone(provider.last_usage)

    def test_ollama_done_is_terminal_and_truncation_is_an_error(self):
        body = b'{"message":{"content":"Hello"},"done":false}\n'
        done = b'{"message":{"content":"!"},"done":true,"prompt_eval_count":4,"eval_count":2}\n'
        provider = OllamaProvider(replace(self.settings, provider='ollama'))
        response = response_bytes(body, done, b'not read after done')
        with patch('agent.providers.requests.post', return_value=response):
            self.assertEqual(''.join(c for c, _ in provider.stream(MESSAGES, Event())), 'Hello!')
        self.assertEqual(provider.last_usage['total_tokens'], 6)
        response.close.assert_called_once()
        for tail in [b'', b'[]\n', b'{"message":[],"done":true}\n', b'{"done":"true"}\n']:
            response = response_bytes(body, tail)
            with self.subTest(tail=tail), patch('agent.providers.requests.post', return_value=response):
                with self.assertRaises(ProviderProtocolError):
                    list(provider.stream(MESSAGES, Event()))
                self.assertIsNone(provider.last_usage)
            response.close.assert_called_once()

    def test_cancel_prevents_request_or_closes_active_connection(self):
        for provider in [LocalServerProvider(self.settings), OllamaProvider(replace(self.settings, provider='ollama'))]:
            with self.subTest(provider=type(provider).__name__):
                cancel = Event()
                cancel.set()
                with patch('agent.providers.requests.post') as post:
                    self.assertEqual(list(provider.stream(MESSAGES, cancel)), [])
                post.assert_not_called()
                cancel.clear()
                body = sse({'choices': [{'delta': {'content': 'Partial'}}]}) if isinstance(provider, LocalServerProvider) else b'{"message":{"content":"Partial"}}\n'
                response = response_bytes(body)
                with patch('agent.providers.requests.post', return_value=response):
                    stream = provider.stream(MESSAGES, cancel)
                    self.assertEqual(next(stream)[0], 'Partial')
                    cancel.set()
                    self.assertEqual(list(stream), [])
                response.close.assert_called_once()
                self.assertIsNone(provider.last_usage)

    def test_redirects_and_invalid_synchronous_answers_close_connections(self):
        for provider in [LocalServerProvider(self.settings), OllamaProvider(replace(self.settings, provider='ollama'))]:
            with self.subTest(provider=type(provider).__name__):
                for action in ['stream', 'generate']:
                    response = response_bytes()
                    response.is_redirect = True
                    with patch('agent.providers.requests.post', return_value=response), self.assertRaises(ProviderProtocolError):
                        list(provider.stream(MESSAGES, Event())) if action == 'stream' else provider.generate(MESSAGES)
                    response.close.assert_called_once()
                for payload in [[], {'message': {'content': 5}}, {'choices': [{'message': {'content': '   '}}]}]:
                    response = response_bytes()
                    response.json.return_value = payload
                    with patch('agent.providers.requests.post', return_value=response), self.assertRaises(RuntimeError):
                        provider.generate(MESSAGES)
                    response.close.assert_called_once()
                    self.assertIsNone(provider.last_usage)


class HTTPIntegrationTests(unittest.TestCase):
    """Exercise real Requests framing and the app's persistence/error contract."""
    def setUp(self):
        self.request_received = Event()
        self.first_read = Event()
        received, first_read = self.request_received, self.first_read

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                received.set()
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(sse({'choices': [{'delta': {'content': 'First'}}]}))
                self.wfile.flush()
                # A reader waiting for a large byte buffer will deadlock here.
                first_read.wait(3)
                if self.path.startswith('/complete/'):
                    try:
                        self.wfile.write(b'data: [DONE]\n\n')
                        self.wfile.flush()
                    except OSError:
                        pass
                self.close_connection = True

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(provider='localserver', data_dir=self.temp.name,
                                 local_server_url=f'http://127.0.0.1:{self.server.server_port}/complete/v1')

    def shutdown(self):
        self.first_read.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_first_text_is_delivered_before_server_sends_the_remainder(self):
        stream = LocalServerProvider(self.settings).stream(MESSAGES, Event())
        result = []
        failure = []

        def read_first():
            try:
                result.append(next(stream)[0])
            except Exception as exc:
                failure.append(exc)
            finally:
                self.first_read.set()

        reader = Thread(target=read_first)
        reader.start()
        try:
            self.assertTrue(self.request_received.wait(2))
            self.assertTrue(self.first_read.wait(1), 'First delta waited for unrelated bytes')
        finally:
            self.first_read.set()
            reader.join(timeout=5)
        self.assertFalse(reader.is_alive())
        self.assertEqual(failure, [])
        self.assertEqual(result, ['First'])
        self.assertEqual(list(stream), [])

    def test_interrupted_http_stream_is_not_saved_and_next_request_recovers(self):
        settings = replace(self.settings, local_server_url=self.settings.local_server_url.replace('/complete/', '/truncated/'))
        agent = Agent(settings)
        client = TestClient(create_app(settings, agent))
        session = str(uuid4())
        self.first_read.set()
        with self.assertLogs('zenith', level='ERROR'):
            response = client.post('/api/chat/stream', json={'session_id': session, 'message': 'Describe an apple.'})
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        self.assertIn('delta', [event['type'] for event in events])
        self.assertEqual(events[-1]['type'], 'error')
        self.assertNotIn('result', [event['type'] for event in events])
        self.assertEqual(agent.store.history(session), [])
        self.assertFalse(agent.lock.locked())
        self.assertEqual(agent.monitor.summary(all_users=True)['failed'], 1)
        agent.provider.settings = self.settings
        result = agent.answer('Describe an apple.', session)
        self.assertEqual(result['response'], 'First')
        self.assertEqual(len(agent.store.history(session)), 1)


if __name__ == '__main__':
    unittest.main()
