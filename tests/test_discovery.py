"""Model discovery contracts: pagination, bounded transport and offline imports."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.discovery import Discovery, DiscoveryError, LIMIT, main, saved_models
from agent.registry import Catalog
from agent.server import create_app

ROOT = Path(__file__).resolve().parents[1]


class Response:
    status_code = 200
    links = {}
    def __init__(self, data=None, chunks=None, status=200, links=None):
        self.chunks = chunks if chunks is not None else [json.dumps(data).encode()]
        self.status_code = status
        self.links = links or {}
        self.closed = False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def iter_content(self, **kwargs): return iter(self.chunks)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'ZENITH_HOME': self.folder.name, 'HF_HUB_OFFLINE': '0', 'ZENITH_DISCOVERY_OFFLINE': '0'})
        self.env.start()
        self.model = {'id': 'team/fine-tune', 'sha': 'a' * 40, 'pipeline_tag': 'text-generation',
                      'tags': ['base_model:finetune:team/base', 'base_model:team/base'],
                      'cardData': {'base_model': 'team/base', 'license': 'apache-2.0'}, 'downloads': 7}
    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def test_hub_pagination_finetune_metadata_and_cache(self):
        response = Response([self.model], links={'next': {'url': 'https://huggingface.co/api/models?cursor=next-token'}})
        service = Discovery()
        with patch('agent.discovery.requests.get', return_value=response) as get:
            result = service.search(q='fine-tune', page_size=1)
            get.assert_called_once()
            kwargs = get.call_args.kwargs
            self.assertFalse(kwargs['allow_redirects'])
            self.assertNotIn('Authorization', kwargs['headers'])
            self.assertEqual(kwargs['params']['search'], 'fine-tune')
            entry = result['entries'][0]
            self.assertTrue(entry['fine_tuned'])
            self.assertEqual(entry['base_models'], ['team/base'])
            self.assertFalse(entry['runtime_verified'])
            self.assertTrue(result['has_more'])
            self.assertEqual(result['next_cursor'], 'next-token')
            result['entries'][0]['id'] = 'changed/value'
            self.assertEqual(service.search(q='fine-tune', page_size=1)['entries'][0]['id'], 'team/fine-tune')
            service.search(q='fine-tune', page_size=1, page=2, cursor='next-token')
            self.assertEqual(get.call_args.kwargs['params']['cursor'], 'next-token')
        self.assertTrue(response.closed)

    def test_hostile_continuation_is_never_requested(self):
        for url in ['http://huggingface.co/api/models?cursor=x', 'https://evil.invalid/api/models?cursor=x',
                    'https://huggingface.co/api/other?cursor=x', 'https://huggingface.co@evil.invalid/api/models?cursor=x']:
            with self.subTest(url=url), patch('agent.discovery.requests.get', return_value=Response([], links={'next': {'url': url}})) as get:
                with self.assertRaises(DiscoveryError): Discovery().search()
                get.assert_called_once()

    def test_github_search_limits_and_incomplete_results(self):
        data = {'items': [{'full_name': 'team/model', 'description': 'Implementation', 'stargazers_count': 9,
                           'license': {'spdx_id': 'MIT'}}], 'total_count': 5000, 'incomplete_results': True}
        with patch('agent.discovery.requests.get', return_value=Response(data)) as get:
            result = Discovery().search('github', q='topic:llm', page_size=50, page=20)
            self.assertFalse(result['has_more'])
            self.assertIn('incomplete', result['notice'])
            self.assertEqual(result['entries'][0]['runtime_support'], 'reference_only')
            self.assertEqual(get.call_args.kwargs['params']['q'], 'topic:llm')
            with self.assertRaises(ValueError): Discovery().search('github', page_size=50, page=21)

    def test_restricted_source_errors_close_and_do_not_expose_payload(self):
        for status in [302, 401, 403, 404, 429, 503]:
            response = Response({'secret': 'upstream-private-value'}, status=status)
            with self.subTest(status=status), patch('agent.discovery.requests.get', return_value=response):
                with self.assertRaises(DiscoveryError) as error: Discovery().search()
                self.assertNotIn('upstream-private-value', str(error.exception))
                self.assertTrue(response.closed)
        for chunks in [[b'x' * (LIMIT + 1)], [b'not json'], [b'\xff']]:
            response = Response(chunks=chunks)
            with patch('agent.discovery.requests.get', return_value=response):
                with self.assertRaises(DiscoveryError): Discovery().search()
                self.assertTrue(response.closed)

    def test_offline_and_busy_never_send_a_request(self):
        with patch('agent.discovery.requests.get') as get:
            with patch.dict(os.environ, {'HF_HUB_OFFLINE': '1'}):
                with self.assertRaises(DiscoveryError): Discovery().search()
            service = Discovery(); service._slots.acquire(); service._slots.acquire()
            with self.assertRaises(DiscoveryError): service.search()
            get.assert_not_called()

    def test_metadata_import_is_atomic_deduplicated_and_searchable_offline(self):
        with patch('agent.discovery.requests.get', return_value=Response(self.model)) as get:
            service = Discovery()
            result = service.add('huggingface', 'team/fine-tune')
            service.add('huggingface', 'team/fine-tune')
            self.assertFalse(result['entry']['runtime_verified'])
            self.assertEqual(len(json.loads(Path(result['saved_to']).read_text())['entries']), 1)
            self.assertEqual(get.call_count, 1)
        with patch.dict(os.environ, {'HF_HUB_OFFLINE': '1'}), patch('agent.discovery.requests.get') as get:
            rows = Catalog().search(q='team/fine-tune')['entries']
            self.assertEqual(rows[0]['revision'], 'a' * 40)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['list']), 0)
            self.assertEqual(len(json.loads(output.getvalue())['entries']), 1)
            get.assert_not_called()

    def test_corrupted_local_library_is_rejected_without_overwrite(self):
        path = Path(self.folder.name) / 'model-library.json'
        for entry in [None, {'source':'unknown'}, {'source':'huggingface','kind':'model','id':'team/model','url':'https://evil.invalid/model'}]:
            original = json.dumps({'schema_version':1,'entries':[entry]})
            path.write_text(original)
            with self.assertRaises(ValueError): saved_models()
            self.assertEqual(path.read_text(), original)

    def test_bad_identifiers_and_mismatched_imports_never_change_library(self):
        with patch('agent.discovery.requests.get') as get:
            for identifier in ['../secret', 'team/../../secret', 'https://bad/model', 'team/model?x', 'team/model/extra']:
                with self.subTest(id=identifier), self.assertRaises(ValueError): Discovery().add('huggingface', identifier)
            get.assert_not_called()
        with patch('agent.discovery.requests.get', return_value=Response(self.model)):
            with self.assertRaises(DiscoveryError): Discovery().add('huggingface', 'different/model')
        self.assertFalse((Path(self.folder.name) / 'model-library.json').exists())

    def test_api_access_gate_validation_and_upstream_failures(self):
        settings = Settings(provider='ollama', data_dir=self.folder.name, api_token='test-private-server-token')
        agent = Agent(settings, provider=object())
        app = create_app(settings, agent)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            self.assertEqual(client.get('/api/discovery').status_code, 401)
            headers = {'Authorization': 'Bearer ' + settings.api_token}
            self.assertEqual(client.get('/api/discovery?source=invalid', headers=headers).status_code, 422)
            with patch.object(app.state.discovery, 'search', side_effect=DiscoveryError('Source rate limited')):
                response = client.get('/api/discovery', headers=headers)
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()['detail'], 'Source rate limited')
            with patch.object(app.state.discovery, 'search', return_value={'entries': [], 'has_more': False}) as search:
                self.assertEqual(client.get('/api/discovery?q=Qwen', headers=headers).status_code, 200)
                search.assert_called_once_with('huggingface', 'model', 'Qwen', 1, 20, '')

    def test_failed_cli_search_returns_failure(self):
        with patch.object(Discovery, 'search', side_effect=DiscoveryError('Source rate limited')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['search']), 1)

    @unittest.skipIf(os.name == 'nt', 'Bash activation is checked on Linux')
    def test_activation_selects_environment_and_restores_shell(self):
        with tempfile.TemporaryDirectory(prefix='zenith activation spaces ') as folder:
            path = Path(folder)
            (path / 'activate.sh').write_bytes((ROOT / 'activate.sh').read_bytes())
            subprocess.run([__import__('sys').executable, '-m', 'venv', '--without-pip', str(path / '.venv')], check=True)
            result = subprocess.run(['bash', '-ec', 'source "$1/activate.sh"; python -c "import sys; assert sys.prefix != sys.base_prefix"; deactivate; test -z "${VIRTUAL_ENV:-}"', 'zenith-test', folder], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('environment active', result.stdout)
            result = subprocess.run(['bash', str(path / 'activate.sh')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('source ./activate.sh', result.stderr)

    def test_pip_check_message_and_failure_are_distinct(self):
        spec = importlib.util.spec_from_file_location('zenith_installer_dependencies', ROOT / 'install.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        with patch.object(installer.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'No broken requirements found.\n', '')), contextlib.redirect_stdout(io.StringIO()) as output:
            installer.run(['python', '-m', 'pip', 'check'])
        self.assertIn('Dependencies verified', output.getvalue())
        self.assertNotIn('broken requirements', output.getvalue())
        with patch.object(installer.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, 'Conflicting fixture package\n', '')), contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(subprocess.CalledProcessError): installer.run(['python', '-m', 'pip', 'check'])
        self.assertIn('Conflicting fixture package', output.getvalue())
