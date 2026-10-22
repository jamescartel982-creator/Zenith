"""Offline catalog contract checks; fixture IDs are intentionally synthetic."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.registry import Catalog, EXPECTED_COUNTS
from agent.server import create_app

STAMP = '2026-10-22T00:00:00Z'


def fixture_documents(full=False):
    documents = {}
    sizes = {('huggingface', 'model'): 3, ('github', 'model'): 2,
             ('huggingface', 'dataset'): 1, ('github', 'dataset'): 1}
    for (source, kind), expected in EXPECTED_COUNTS.items():
        entries = []
        for i in range(expected if full else sizes[source, kind]):
            identifier = f'fixture-owner/{source}-{kind}-{i}'
            prefix = 'https://github.com/' if source == 'github' else 'https://huggingface.co/' + ('datasets/' if kind == 'dataset' else '')
            entries.append({
                'id': identifier, 'name': identifier, 'source': source, 'kind': kind,
                'url': prefix + identifier, 'description': 'A coding reference' if i == 0 else 'A math reference',
                'task': 'text-generation' if kind == 'model' else 'question-answering',
                'license': 'unknown', 'tags': ['coding' if i == 0 else 'math'],
                'popularity_rank': i + 1, 'observed_at': STAMP,
                'provenance': {'method': 'synthetic offline test fixture'},
                'runtime_support': 'huggingface' if source == 'huggingface' and kind == 'model' else 'reference_only',
                'runtime_verified': False,
            })
        documents[source, kind] = {'schema_version': 1, 'source': source, 'kind': kind,
                                   'generated_at': STAMP, 'selection': 'Synthetic fixtures for tests only', 'entries': entries}
    return documents


def write_documents(directory, documents):
    for (source, kind), document in documents.items():
        (Path(directory) / f'{source}_{kind}s.json').write_text(json.dumps(document), encoding='utf-8')


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.documents = fixture_documents()
        write_documents(self.directory.name, self.documents)
        self.catalog = Catalog(self.directory.name, strict=False)

    def test_counts_and_get_are_source_scoped(self):
        self.assertEqual(self.catalog.counts, {
            'models': 5, 'datasets': 2, 'huggingface_models': 3, 'github_models': 2,
            'huggingface_datasets': 1, 'github_datasets': 1})
        entry = self.catalog.get('huggingface', 'model', 'FIXTURE-OWNER/HUGGINGFACE-MODEL-0')
        self.assertEqual(entry['id'], 'fixture-owner/huggingface-model-0')
        with self.assertRaises(ValueError):
            self.catalog.get('github', 'model', entry['id'])
        with self.assertRaises(ValueError):
            self.catalog.get('huggingface', 'dataset', entry['id'])

    def test_production_requires_exact_counts(self):
        with self.assertRaisesRegex(ValueError, '500 sourced entries'):
            Catalog(self.directory.name)
        write_documents(self.directory.name, fixture_documents(full=True))
        self.assertEqual(Catalog(self.directory.name).counts['models'], 1000)
        self.assertEqual(Catalog(self.directory.name).counts['datasets'], 200)

    def test_search_filters_paginates_and_preserves_global_counts(self):
        result = self.catalog.search(kind='model', source='huggingface', q='MATH', page=1, page_size=1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['entries'][0]['popularity_rank'], 2)
        self.assertEqual(result['counts']['models'], 5)
        second = self.catalog.search(kind='model', source='huggingface', q='math', page=2, page_size=1)
        self.assertEqual(second['entries'][0]['popularity_rank'], 3)
        self.assertEqual(self.catalog.search(q='not-a-matching-keyword')['total'], 0)
        self.assertEqual(self.catalog.search(page=100, page_size=10)['entries'], [])

    def test_configuration_flags_do_not_turn_repository_references_into_models(self):
        hf = 'fixture-owner/huggingface-model-0'
        gh = 'fixture-owner/github-model-0'
        rows = self.catalog.search(configured={hf, gh})['entries']
        flags = {row['id']: row['configured_for_chat'] for row in rows}
        self.assertTrue(flags[hf])
        self.assertFalse(flags[gh])
        self.assertFalse(any(row['configured_for_chat'] for row in self.catalog.search(kind='dataset', configured={hf})['entries']))
        self.assertNotIn('configured_for_chat', self.catalog.get('huggingface', 'model', hf))

    def test_schema_sources_and_runtime_claims_are_validated(self):
        mutations = [
            (('huggingface', 'model'), lambda d: d.update(schema_version=2)),
            (('github', 'model'), lambda d: d.update(source='huggingface')),
            (('github', 'model'), lambda d: d['entries'][0].update(url='https://evil.example/model')),
            (('huggingface', 'dataset'), lambda d: d['entries'][0].update(id='../dataset')),
            (('huggingface', 'model'), lambda d: d['entries'][0].update(provenance=None)),
            (('huggingface', 'model'), lambda d: d['entries'][0].update(runtime_verified=True)),
            (('github', 'model'), lambda d: d['entries'][0].update(runtime_support='huggingface')),
            (('huggingface', 'model'), lambda d: d.update(generated_at='not-a-date')),
        ]
        for key, mutate in mutations:
            with self.subTest(key=key, mutation=mutate):
                documents = copy.deepcopy(self.documents)
                mutate(documents[key])
                write_documents(self.directory.name, documents)
                with self.assertRaises(ValueError):
                    Catalog(self.directory.name, strict=False)

    def test_duplicate_ids_are_rejected_case_insensitively(self):
        entry = self.documents['huggingface', 'model']['entries'][0]
        duplicate = copy.deepcopy(entry)
        duplicate['id'] = duplicate['id'].upper()
        duplicate['url'] = 'https://huggingface.co/' + duplicate['id']
        self.documents['huggingface', 'model']['entries'].append(duplicate)
        write_documents(self.directory.name, self.documents)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            Catalog(self.directory.name, strict=False)

    def test_invalid_filters_and_limits_are_rejected(self):
        for kwargs in ({'kind': 'tool'}, {'source': 'unknown'}, {'page': 0}, {'page_size': 101}, {'q': 'x' * 201}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.catalog.search(**kwargs)


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        write_documents(self.directory.name, fixture_documents())
        self.catalog = Catalog(self.directory.name, strict=False)
        self.settings = Settings(provider='huggingface', model='fixture-owner/huggingface-model-0',
                                 data_dir=str(Path(self.directory.name) / 'data'), api_token='t' * 40)
        self.provider = Mock()
        self.provider.generate.side_effect = lambda messages: ('Fixture answer', messages)
        self.agent = Agent(self.settings, provider=self.provider)
        self.client = TestClient(create_app(self.settings, self.agent, catalog=self.catalog))
        self.headers = {'Authorization': 'Bearer ' + self.settings.api_token}

    def test_catalog_team_and_knowledge_require_authentication(self):
        for path in ('/api/catalog', '/api/team', '/api/knowledge'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get('/api/knowledge', headers=self.headers).json(), {'documents': 0, 'total_sources': 0})
        team = self.client.get('/api/team', headers=self.headers).json()
        self.assertEqual(team['mode'], 'single')
        self.assertEqual(team['members'][0]['model'], self.settings.model)

    def test_catalog_api_pagination_configuration_and_input_validation(self):
        result = self.client.get('/api/catalog', params={'source': 'huggingface', 'kind': 'model', 'q': 'coding', 'page_size': 1}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body['total'], 1)
        self.assertTrue(body['entries'][0]['configured_for_chat'])
        self.assertEqual(body['counts']['models'], 5)
        for params in ({'source': 'not-a-source'}, {'kind': 'code'}, {'page': 0}, {'page_size': 101}, {'q': 'x' * 201}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/catalog', params=params, headers=self.headers).status_code, 422)

    def test_imported_knowledge_is_visible_without_creating_chat_history(self):
        self.agent.store.add_document('fixture:source', 'https://huggingface.co/datasets/fixture-owner/data', 'Glaciers store freshwater.')
        stats = self.client.get('/api/knowledge', headers=self.headers).json()
        self.assertEqual(stats, {'documents': 1, 'total_sources': 1})
        session = str(uuid4())
        self.assertEqual(self.client.get('/api/history/' + session, headers=self.headers).json()['turns'], [])
