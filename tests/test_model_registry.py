"""Registry invariants and actual HTTP adapter round trips (no paid calls)."""
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from threading import Event, Thread
import time
import unittest
from unittest.mock import patch
import requests
from agent.config import Settings
from agent.model_capabilities import ModelCapabilities, ModelRecord
from agent.model_registry import ModelRegistry, build_registry, external_declarations
from agent.provider_adapters.anthropic_adapter import AnthropicAdapter
from agent.provider_adapters.openai_adapter import OpenAIAdapter
from agent.provider_adapters.common import AdapterError, CallContext, Cancelled, request_json


@contextmanager
def api_server(callback):
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self): self.respond()
        def do_POST(self): self.respond()
        def log_message(self, *args): pass
        def respond(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            payload = json.loads(body) if body else None
            calls.append((self.command, self.path, payload))
            status, data = callback(self.command, self.path, payload)
            encoded = json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = Thread(target=server.serve_forever)
    worker.start()
    def transport(method, url, **kwargs):
        # Production URL fixed by adapter; test transport maps it to a real socket.
        path = '/' + url.split('/v1/', 1)[1]
        return requests.request(method, f'http://127.0.0.1:{server.server_port}' + path, **kwargs)
    try:
        yield transport, calls
    finally:
        server.shutdown(); server.server_close(); worker.join()


def context(): return CallContext(time.monotonic() + 5, max_output_tokens=32)


class RegistryTests(unittest.TestCase):
    def test_native_preserves_identity_and_optional_providers_disabled(self):
        with patch.dict(os.environ, {'ZENITH_EXTERNAL_MODELS': '[]', 'ZENITH_NATIVE_PROVIDER': 'huggingface'}):
            settings = Settings(provider='huggingface', model='existing/zenith', adapter='/existing/adapter')
            registry = build_registry(settings)
        record = registry.get(registry.native_key)
        self.assertEqual(record.model_id, settings.model)
        self.assertTrue(record.routable)
        self.assertEqual(registry.adapters['huggingface'].bindings[record.key].adapter, settings.adapter)
        self.assertTrue(all(not r.routable for r in registry.records.values() if r.provider in {'openai', 'anthropic'}))
        mythos = next(x for x in registry.public()['families']['anthropic'] if x['name'] == 'Mythos')
        self.assertNotIn('available', mythos)

    def test_plugin_refresh_revokes_stale_access(self):
        class Adapter:
            name = 'plugin'
            def discover(self, context): raise AdapterError('access_denied')
            def generate(self, *args): raise AssertionError('must not infer')
        r = ModelRegistry(); r.register_adapter(Adapter())
        key = r.register(ModelRecord('plugin', 'model', 'listed', configured=True))
        self.assertFalse(r.refresh('plugin'))
        self.assertFalse(r.get(key).routable)
        self.assertEqual(r.discovery_status['plugin']['code'], 'access_denied')

    def test_account_discovery_does_not_enable_every_model(self):
        def serve(*args):
            return 200, {'data': [{'id': 'exact-a'}, {'id': 'restricted-b'}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only', 'ZENITH_EXTERNAL_MODELS': json.dumps([
                {'provider': 'openai', 'model_id': 'exact-a', 'api': 'responses', 'context_window': 8192}])}), api_server(serve) as (transport, calls):
            r = build_registry(Settings()); r.adapters['openai'] = OpenAIAdapter(transport)
            self.assertTrue(r.refresh('openai', context()))
            self.assertTrue(r.get('openai:exact-a').routable)
            self.assertFalse(r.get('openai:restricted-b').routable)
            self.assertEqual(r.get('openai:restricted-b').capabilities.input_modalities, ())
            self.assertNotIn('test-only', json.dumps(r.public()))
            self.assertEqual(len(calls), 1)

    def test_missing_credentials_makes_no_http_call(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'ANTHROPIC_API_KEY': ''}):
            for adapter in (OpenAIAdapter(lambda *a, **k: self.fail('network')), AnthropicAdapter(lambda *a, **k: self.fail('network'))):
                with self.assertRaisesRegex(AdapterError, 'credential_missing'): adapter.discover(context())

    def test_config_rejects_unsafe_or_unsourced_claims(self):
        for row in ({'provider': 'openai', 'model_id': 'x'},
                    {'provider': 'openai', 'model_id': 'x', 'api': 'responses', 'api_key': 'never'},
                    {'provider': 'anthropic', 'model_id': 'x', 'pricing': {'input_usd_per_million': -1}}):
            with patch.dict(os.environ, {'ZENITH_EXTERNAL_MODELS': json.dumps([row])}):
                with self.assertRaises(ValueError): external_declarations()

    def test_openai_actual_http_completion(self):
        def serve(method, path, payload):
            self.assertEqual(path, '/responses')
            self.assertFalse(payload['store'])
            self.assertNotIn('tools', payload)
            return 200, {'model': 'exact', 'status': 'completed', 'output': [
                {'type': 'reasoning', 'summary': []}, {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': '4'}]}],
                'usage': {'input_tokens': 7, 'output_tokens': 2}}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), api_server(serve) as (transport, calls):
            adapter = OpenAIAdapter(transport)
            record = ModelRecord('openai', 'exact', capabilities=ModelCapabilities(extra={'api': 'responses'}))
            result = adapter.generate(record, [{'role': 'user', 'content': '2+2'}], context())
            self.assertEqual(result.text, '4'); self.assertEqual(result.usage['total_tokens'], 9)

    def test_openai_rejects_incomplete_and_unrequested_tools(self):
        for data in ({'status': 'incomplete'}, {'status': 'completed', 'output': [{'type': 'function_call', 'name': 'shell'}]}):
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), api_server(lambda *args: (200, data)) as (transport, calls):
                record = ModelRecord('openai', 'exact', capabilities=ModelCapabilities(extra={'api': 'responses'}))
                with self.assertRaises(AdapterError): OpenAIAdapter(transport).generate(record, [{'role': 'user', 'content': 'x'}], context())

    def test_anthropic_pagination_capabilities_and_retirement(self):
        def serve(method, path, payload):
            if 'after_id=' not in path:
                return 200, {'data': [{'id': 'claude-mythos-exact', 'line': 'mythos', 'lifecycle': 'active', 'max_input_tokens': 32768,
                    'capabilities': {'image_input': {'supported': True}, 'effort': {'high': {'supported': True}}}}], 'has_more': True, 'last_id': 'cursor'}
            return 200, {'data': [{'id': 'old', 'lifecycle': 'retired'}], 'has_more': False}
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), api_server(serve) as (transport, calls):
            rows = AnthropicAdapter(transport).discover(context())
            self.assertEqual(len(calls), 2); self.assertEqual(rows[0].family, 'mythos')
            self.assertIn('image', rows[0].capabilities.input_modalities)
            self.assertFalse(rows[0].routable)  # Account listing alone is not opt-in.
            self.assertEqual(rows[1].availability, 'unavailable')

    def test_anthropic_actual_http_completion_and_system_separation(self):
        def serve(method, path, payload):
            self.assertEqual(payload['system'], 'Follow policy')
            self.assertEqual(payload['messages'], [{'role': 'user', 'content': 'hello'}])
            return 200, {'model': 'exact', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'hello'}],
                         'usage': {'input_tokens': 4, 'output_tokens': 2, 'cache_read_input_tokens': 3}}
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), api_server(serve) as (transport, calls):
            result = AnthropicAdapter(transport).generate(ModelRecord('anthropic', 'exact'),
                [{'role': 'system', 'content': 'Follow policy'}, {'role': 'user', 'content': 'hello'}], context())
            self.assertEqual(result.text, 'hello'); self.assertEqual(result.usage['total_tokens'], 9)

    def test_cancellation_deadline_and_error_redaction(self):
        c = context(); c.cancel.set()
        with self.assertRaises(Cancelled): request_json('GET', 'https://api.openai.com/v1/models', c)
        with self.assertRaisesRegex(AdapterError, 'deadline'): request_json('GET', 'unused', CallContext(0))
        with api_server(lambda *a: (403, {'error': 'secret-that-must-not-escape'})) as (transport, calls):
            with self.assertRaises(AdapterError) as raised:
                request_json('GET', 'https://api.openai.com/v1/models', context(), request=transport)
            self.assertEqual(str(raised.exception), 'access_denied')

    def test_local_registry_rejects_remote_server(self):
        with patch.dict(os.environ, {'ZENITH_NATIVE_PROVIDER': 'ollama', 'ZENITH_EXTERNAL_MODELS': '[]'}):
            with self.assertRaisesRegex(ValueError, 'loopback'):
                build_registry(Settings(ollama_url='https://example.org'))

    def test_capability_metadata_rejects_invalid_limits_prices_and_flags(self):
        for fields in ({'context_window': '32768'}, {'context_window': -1}, {'max_output_tokens': True},
                       {'tools': 'false'}, {'input_modalities': 'text'}, {'tags': ('coding', 1)},
                       {'pricing': {'input_usd_per_million': -1, 'source': 'https://example.org/pricing'}},
                       {'pricing': {'input_usd_per_million': float('nan'), 'source': 'https://example.org/pricing'}}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                ModelCapabilities(**fields)

    def test_invalid_discovery_metadata_fails_closed_before_routing(self):
        class BadMetadata:
            name = 'plugin'
            def discover(self, context):
                return [ModelRecord('plugin', 'model', 'listed', configured=True,
                        capabilities=ModelCapabilities(context_window='invalid'))]
            def generate(self, *args): raise AssertionError('Invalid metadata cannot invoke a model')
        registry = ModelRegistry(); registry.register_adapter(BadMetadata())
        key = registry.register(ModelRecord('plugin', 'model', 'listed', configured=True))
        self.assertFalse(registry.refresh('plugin', context()))
        self.assertFalse(registry.get(key).routable)

    def test_invalid_measurements_cannot_poison_routing(self):
        registry = ModelRegistry(); registry.register_adapter(OpenAIAdapter())
        key = registry.register(ModelRecord('openai', 'model'))
        for measurement in (float('nan'), float('inf'), True, '10', -1):
            with self.subTest(measurement=measurement), self.assertRaises(ValueError):
                registry.observe(key, measurement)
        self.assertEqual(registry.metrics, {})

    def test_model_privacy_and_availability_flags_are_not_coerced(self):
        for fields in ({'local': 'false'}, {'configured': 1}, {'availability': 'automatically-approved'},
                       {'lifecycle': 'probably-active'}, {'capabilities': {}}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                ModelRecord('plugin', 'model', **fields)
