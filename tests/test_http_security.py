"""Executable HTTP trust-boundary and private-storage regressions."""
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.http_security import MAX_REQUEST_BYTES, RequestSecurityMiddleware
from agent.server import create_app
from agent.storage import Store


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings = Settings(provider='huggingface', data_dir=folder.name,
                                 api_token='', allowed_hosts=('localhost', '127.0.0.1', '::1'))
        self.provider = Mock()
        self.agent = Agent(self.settings, self.provider)
        self.client = TestClient(create_app(self.settings, self.agent), base_url='http://127.0.0.1')

    def test_dns_rebinding_and_duplicate_host_are_rejected_before_api_access(self):
        for host in ('attacker.example', 'localhost.attacker.example', '127.0.0.1.attacker.example', 'localhost@attacker.example', 'localhost:bad'):
            with self.subTest(host=host):
                self.assertEqual(self.client.get('/api/account', headers={'Host': host}).status_code, 400)
        self.assertEqual(self.client.get('/api/account', headers=[('Host', 'localhost'), ('Host', 'attacker.example')]).status_code, 400)
        self.provider.generate.assert_not_called()

    def test_loopback_ipv4_ipv6_and_localhost_remain_available(self):
        for origin in ('http://127.0.0.1', 'http://localhost:7860', 'http://[::1]:7860'):
            with self.subTest(origin=origin):
                client = TestClient(self.client.app, base_url=origin)
                self.assertEqual(client.get('/healthz').status_code, 200)
                self.assertEqual(client.get('/api/account').status_code, 200)

    def test_remote_host_requires_explicit_configuration_and_server_authentication(self):
        with self.assertRaises(ValueError):
            replace(self.settings, allowed_hosts=('chat.example',))
        for host in ('*', '*.example', 'https://chat.example', 'chat.example:7860', 'bad..example'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                replace(self.settings, api_token='a'*40, allowed_hosts=(host,))
        settings = replace(self.settings, api_token='a'*40, allowed_hosts=('chat.example', '127.0.0.1'))
        client = TestClient(create_app(settings, self.agent), base_url='https://chat.example')
        self.assertEqual(client.get('/api/account').status_code, 401)
        self.assertEqual(client.get('/api/account', headers={'Authorization': 'Bearer '+'a'*40}).status_code, 200)

    def test_cross_site_api_reads_and_writes_without_origin_are_rejected(self):
        headers = {'Sec-Fetch-Site': 'cross-site'}
        self.assertEqual(self.client.get('/api/account', headers=headers).status_code, 403)
        self.assertEqual(self.client.post('/api/account/logout', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/account', headers={'Sec-Fetch-Site': 'same-origin'}).status_code, 200)

    def test_invalid_credentials_are_not_echoed_by_validation(self):
        password = 'private-password-' * 30
        response = self.client.post('/api/account/login', json={'username': 'alice', 'password': password})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(password, response.text)
        self.assertNotIn('input', response.text)
        self.assertIn('detail', response.json())

    def test_oversized_bodies_are_rejected_and_valid_json_still_works(self):
        response = self.client.post('/api/account/register', content=b'x'*(MAX_REQUEST_BYTES+1), headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertIn('frame-ancestors', response.headers['content-security-policy'])
        self.assertEqual(self.client.post('/api/account/register', json={
            'username': 'alice', 'display_name': 'Alice', 'password': 'long-enough-password'}).status_code, 200)


class StreamingBodyBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, messages, *, headers=None, timeout=0.1, maximum=8, stall=False):
        called, sent = [], []

        async def target(scope, receive, send):
            called.append(await receive())
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})

        async def receive():
            if messages:
                return messages.pop(0)
            if stall:
                await asyncio.sleep(10)
            return {'type': 'http.disconnect'}

        async def send(message):
            sent.append(message)

        scope = {'type': 'http', 'http_version': '1.1', 'method': 'POST', 'path': '/api/account/login',
                 'headers': [(b'host', b'localhost')] + (headers or [])}
        await RequestSecurityMiddleware(target, ('localhost',), max_body_bytes=maximum, body_timeout=timeout)(scope, receive, send)
        return called, sent

    async def test_chunked_oversize_without_content_length_never_reaches_parser(self):
        called, sent = await self.invoke([
            {'type': 'http.request', 'body': b'12345', 'more_body': True},
            {'type': 'http.request', 'body': b'6789', 'more_body': False}])
        self.assertFalse(called)
        self.assertEqual(sent[0]['status'], 413)

    async def test_bounded_chunks_are_delivered_exactly_once(self):
        called, sent = await self.invoke([
            {'type': 'http.request', 'body': b'ab', 'more_body': True},
            {'type': 'http.request', 'body': b'cd', 'more_body': False}])
        self.assertEqual(called[0]['body'], b'abcd')
        self.assertFalse(called[0]['more_body'])
        self.assertEqual(sent[0]['status'], 200)

    async def test_slow_body_times_out_before_routing(self):
        called, sent = await self.invoke([], stall=True, timeout=0.01)
        self.assertFalse(called)
        self.assertEqual(sent[0]['status'], 408)

    async def test_ambiguous_or_invalid_length_is_rejected_before_receive(self):
        for headers in ([(b'content-length', b'1'), (b'content-length', b'1')],
                        [(b'content-length', b'1'), (b'transfer-encoding', b'chunked')],
                        [(b'content-length', b'-1')]):
            called, sent = await self.invoke([], headers=headers)
            self.assertFalse(called)
            self.assertEqual(sent[0]['status'], 400)


@unittest.skipUnless(os.name == 'posix', 'POSIX file modes; Windows needs NTFS ACLs')
class PrivateStorageTests(unittest.TestCase):
    def test_group_or_world_writable_data_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'shared'
            root.mkdir()
            root.chmod(0o777)
            with self.assertRaises(PermissionError):
                Store(root)
            self.assertFalse((root / 'zenith.sqlite3').exists())

    def test_new_database_and_sidecars_are_private_even_with_permissive_umask(self):
        with tempfile.TemporaryDirectory() as folder:
            old_mask = os.umask(0)
            try:
                root = Path(folder) / 'private'
                store = Store(root)
                self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(store.path.stat().st_mode), 0o600)
                with store.connect() as db:
                    db.execute('CREATE TABLE privacy_test(value TEXT)')
                    for suffix in ('-wal', '-shm'):
                        path = Path(str(store.path)+suffix)
                        if path.exists():
                            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            finally:
                os.umask(old_mask)

    def test_existing_database_permissions_tighten_without_losing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.add('session', 'private question', 'private answer', [], 'unchanged-model')
            store.path.chmod(0o644)
            restored = Store(folder)
            self.assertEqual(stat.S_IMODE(restored.path.stat().st_mode), 0o600)
            with restored.connect() as db:
                self.assertEqual(db.execute('SELECT response FROM turns').fetchone()[0], 'private answer')

    def test_symlinked_database_is_rejected_without_changing_its_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'unrelated'
            target.write_text('preserve')
            target.chmod(0o644)
            (root / 'zenith.sqlite3').symlink_to(target)
            with self.assertRaises(OSError):
                Store(root)
            self.assertEqual(target.read_text(), 'preserve')
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
