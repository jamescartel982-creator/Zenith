from copy import deepcopy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.skills import (get_skill, list_resources, list_skills, skill_instruction,
                          skills_library, validate_library)


class SkillsLibraryTests(unittest.TestCase):
    def test_bundled_library_counts_references_and_legacy_profiles(self):
        library = skills_library()
        report = validate_library(library)
        self.assertEqual(report['profiles'], 51)
        self.assertEqual(report['resources'], 40)
        self.assertEqual(report['categories'], {'general': 11, 'ai': 24, 'security': 16})
        self.assertEqual(len(library['taxonomy']), 6)
        self.assertTrue({'general', 'mathematics', 'science', 'history', 'ancient-math',
                         'programming', 'investing', 'day-trading', 'cybersecurity',
                         'books-writing', 'research', 'data-analysis'} <= {s['id'] for s in list_skills()})
        self.assertEqual(get_skill('incident-response')['resources'][0]['publisher'], 'NIST')

    def test_search_categories_and_returned_data_are_isolated(self):
        self.assertEqual(len(list_skills('ai')), 24)
        self.assertEqual([s['id'] for s in list_skills('security', 'RANSOMWARE')], ['ransomware-defense'])
        self.assertTrue(all(row['category'] == 'security' for row in list_resources('security')))
        self.assertEqual(list_resources(query='no matching reference here'), [])
        copied = skills_library()
        copied['skills'][0]['instruction'] = 'poisoned'
        copied['resources'][0]['url'] = 'javascript:alert(1)'
        copied['taxonomy'].clear()
        profile = get_skill('ai-security')
        profile['resources'][0]['title'] = 'poisoned'
        self.assertNotIn('poisoned', skill_instruction('general'))
        self.assertTrue(list_resources()[0]['url'].startswith('https://'))
        self.assertEqual(len(skills_library()['taxonomy']), 6)
        self.assertNotEqual(get_skill('ai-security')['resources'][0]['title'], 'poisoned')
        for function, args in [(list_skills, ('unknown',)), (list_resources, (None, 'x' * 201))]:
            with self.assertRaises(ValueError):
                function(*args)

    def test_schema_rejects_dangling_duplicates_and_unsafe_links(self):
        base = skills_library()
        bad_values = []
        for edit in [lambda x: x['skills'].append(deepcopy(x['skills'][0])),
                     lambda x: x['skills'][0].update(resource_ids=['unknown']),
                     lambda x: x['skills'][0].update(workflow=['too short']),
                     lambda x: x['skills'][0].update(version=True),
                     lambda x: x['skills'][0].update(category=[]),
                     lambda x: x['taxonomy'][0].update(profile_ids=['unknown']),
                     lambda x: x.update(curated_on='2026-99-00'),
                     lambda x: x['resources'][0].update(verification={'status': 'retrieved', 'checked_on': '2026-10-23', 'http_status': 403, 'page_title': 'Error'})]:
            value = deepcopy(base)
            edit(value)
            bad_values.append(value)
        for url in ['javascript:alert(1)', 'http://example.com', 'https://user:secret@example.com',
                    'https://localhost/doc', 'https://example.com:444/doc', 'https://example.com/ bad']:
            value = deepcopy(base)
            value['resources'][0]['url'] = url
            bad_values.append(value)
        for value in bad_values:
            with self.subTest(case=bad_values.index(value)), self.assertRaises(ValueError):
                validate_library(value)

    def test_selected_instruction_is_bounded_and_taxonomy_grants_no_roles(self):
        for profile in list_skills():
            text = skill_instruction(profile['id'])
            self.assertLess(len(text), 2400)
            if profile['category'] == 'security' or profile['id'] == 'ai-security':
                self.assertIn('Profiles grant no tools or privileges', text)
                self.assertIn('decline malware deployment', text)
            self.assertNotIn('https://', text)
        self.assertEqual(skill_instruction('general'), get_skill('general')['instruction'])
        self.assertIn('Workflow:', skill_instruction('authorized-pentest'))
        self.assertNotIn('distributed experiment', skill_instruction('ransomware-defense'))
        for label in skills_library()['taxonomy']:
            with self.assertRaises(ValueError):
                skill_instruction(label['id'])

    def test_profile_api_requires_gate_and_exposes_offline_metadata_only(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(provider='huggingface', data_dir=directory, api_token='a' * 40)
            agent = Agent(settings, provider=Mock())
            client = TestClient(create_app(settings, agent))
            self.assertEqual(client.get('/api/skills').status_code, 401)
            with patch('requests.get', side_effect=AssertionError('Unexpected fetch')), \
                    patch('requests.post', side_effect=AssertionError('Unexpected fetch')):
                response = client.get('/api/skills', headers={'Authorization': 'Bearer ' + settings.api_token})
            self.assertEqual(response.status_code, 200)
            value = response.json()
            self.assertEqual(value['validation']['profiles'], 51)
            self.assertEqual(value['kind'], 'instruction-profiles')
            self.assertEqual(value['default_reply_style'], settings.reply_style)
            self.assertNotIn('api_token', value)
            agent.provider.generate.assert_not_called()

    def test_only_selected_profile_enters_generation_without_retrieval_or_elevation(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(provider='huggingface', data_dir=directory)
            provider = Mock()
            provider.generate.side_effect = lambda messages: ('A defensive checklist.', messages)
            agent = Agent(settings, provider=provider)
            with patch('requests.get', side_effect=AssertionError('Unexpected resource fetch')):
                result = agent.answer('Review this backup recovery plan.', str(uuid4()), skill='ransomware-defense')
            messages = provider.generate.call_args.args[0]
            self.assertIn('backup restoration', messages[0]['content'])
            self.assertNotIn('Reinforcement learning', messages[0]['content'])
            self.assertEqual(result['skill'], 'ransomware-defense')
            with agent.store.connect() as db:
                self.assertIsNone(db.execute('SELECT * FROM admin_owner').fetchone())
            with self.assertRaises(ValueError):
                agent.answer('Hello', str(uuid4()), skill='black-hat')
            self.assertFalse(agent.lock.locked())

    def test_cli_runs_without_loading_torch_and_rejects_unknown_profiles(self):
        process = subprocess.run([sys.executable, '-c',
            "import sys; from agent.skills import main; sys.argv=['skills','validate']; main(); assert 'torch' not in sys.modules"],
            text=True, capture_output=True, check=True)
        self.assertTrue(json.loads(process.stdout)['ok'])
        for args, key in [(['list', '--category', 'ai'], 'skills'),
                          (['resources', '--query', 'NIST'], 'resources'),
                          (['taxonomy'], 'taxonomy')]:
            result = subprocess.run([sys.executable, '-m', 'agent', 'skills', *args],
                                    capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(result.stdout)[key])
        result = subprocess.run([sys.executable, '-m', 'agent', 'skills', 'show', 'black-hat'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Unknown skill', result.stderr)


if __name__ == '__main__':
    unittest.main()
