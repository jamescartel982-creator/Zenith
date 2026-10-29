"""Real compact-library installation, rendering, auth, persistence and rollback."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.recipe_catalog import RecipeCatalog, cursor_start
from agent import recipe_definitions_v1 as grammar
from agent.skill_catalog import SkillCatalog
from agent.storage import Store
from agent.server import create_app
from test_skill_catalog import example, write_pack


class GeneratedRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='zenith-generated-tests-')
        cls.store = Store(cls.folder.name)
        cls.receipt = RecipeCatalog(cls.store).install(True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_real_count_coordinates_labels_and_restart(self):
        self.assertEqual(self.receipt['installed'], 100000)
        self.assertEqual(self.receipt['independently_evaluated'], 0)
        self.assertFalse(self.receipt['training_performed'])
        reopened = SkillCatalog(Store(self.folder.name))
        self.assertEqual(reopened.status(True)['installed_profiles'], 100000)
        self.assertEqual(reopened.status()['generated_profiles'], 90000)
        for index in (0, 1, 39, 40, 999, 25000, 89999, 90000, 99999):
            profile = reopened.get(grammar.PREFIX + f'{index:05d}')
            self.assertTrue(profile['generated'])
            self.assertIn('not independently evaluated', profile['instruction'])
            self.assertEqual(profile['access'], 'admin' if index >= 90000 else 'public')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT idx) FROM generated_recipes').fetchone()[0], 100000)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM generated_recipe_terms').fetchone()[0], 140)

    def test_multi_dimension_index_exact_identifier_and_bounded_pages(self):
        catalog = SkillCatalog(self.store)
        first = catalog.search('Python correctness beginner', limit=3)
        second = catalog.search('Python correctness beginner', after=first['next'], limit=3)
        self.assertEqual(len(first['skills']), 3)
        self.assertFalse({row['id'] for row in first['skills']} & {row['id'] for row in second['skills']})
        for row in first['skills'] + second['skills']:
            self.assertIn('Python /', row['name'])
            self.assertIn('/ Correctness / Beginner', row['name'])
        self.assertEqual(catalog.search('x-recipes-25000')['skills'][0]['id'], 'x-recipes-25000')
        self.assertEqual(catalog.search('x-recipes-90000')['skills'], [])
        self.assertEqual(catalog.search('x-recipes-90000', include_admin=True)['skills'][0]['access'], 'admin')
        self.assertEqual(catalog.search(category='security')['skills'], [])
        self.assertEqual(catalog.search('noSuchRecipeWord123')['skills'], [])
        # OR is an ordinary searchable word, not a boolean/SQL operator.
        quoted = catalog.search('" OR 1=1 --')['skills']
        self.assertLessEqual(len(quoted), 25)
        self.assertTrue(all(row['access'] == 'public' for row in quoted))
        self.assertEqual(catalog.status(True)['installed_profiles'], 100000)
        self.assertLessEqual(len(catalog.search('generated', limit=100)['skills']), 100)

    def test_arbitrary_cursors_obey_lexical_keyset_order(self):
        for after in ('', 'x-aaa-z', 'x-recipes-', 'x-recipes-0', 'x-recipes-0000z',
                      'x-recipes-00000suffix', 'x-recipes-89999', 'x-recipes-99999', 'z'):
            index = cursor_start(after)
            self.assertTrue(index == grammar.TOTAL or grammar.PREFIX + f'{index:05d}' > after)
            self.assertTrue(index == 0 or grammar.PREFIX + f'{index-1:05d}' <= after)

    def test_idempotence_does_not_overwrite_or_duplicate_entries(self):
        again = RecipeCatalog(self.store).install(True)
        self.assertTrue(again['already_installed'])
        self.assertEqual(again['rendered_sha256'], self.receipt['rendered_sha256'])
        self.assertEqual(RecipeCatalog(self.store).status(True)['installed_profiles'], 100000)
        with self.assertRaises(PermissionError):
            RecipeCatalog(self.store).install()

    def test_full_recipe_library_cannot_silently_evict_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder); catalog = SkillCatalog(store)
            path = Path(folder) / 'pack.jsonl'
            write_pack(path, [example()]); catalog.install(path, True)
            with self.assertRaisesRegex(ValueError, 'insufficient capacity'):
                RecipeCatalog(store).install(True)
            self.assertEqual(catalog.status(True)['imported_profiles'], 1)
            self.assertEqual(catalog.status(True)['generated_profiles'], 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pack.jsonl'; write_pack(path, [example()])
            with self.assertRaisesRegex(ValueError, 'exceed 100000'):
                SkillCatalog(self.store).install(path, True)
        self.assertEqual(SkillCatalog(self.store).status(True)['generated_profiles'], 100000)

    def test_late_bad_recipe_rolls_back_all_new_tables_and_preserves_history(self):
        real_render = grammar.render
        def broken(index):
            value = real_render(index)
            if index == 7:
                value['workflow'] = []
            return value
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder); store.add('old-session', 'old prompt', 'old answer', [], 'preserved')
            with patch.object(grammar, 'render', side_effect=broken):
                with self.assertRaises(ValueError): RecipeCatalog(store).install(True)
            with store.connect() as db:
                self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_recipes'").fetchone())
                self.assertEqual(db.execute('SELECT response FROM turns').fetchone()[0], 'old answer')

    def test_low_disk_duplicate_instructions_and_definition_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with patch('agent.recipe_catalog.shutil.disk_usage', return_value=Mock(free=0)):
                with self.assertRaisesRegex(ValueError, '64 MiB'): RecipeCatalog(store).install(True)
            render = grammar.render
            def duplicate(index):
                value = render(index)
                if index == 1: value['instruction'] = render(0)['instruction']
                return value
            with patch.object(grammar, 'render', side_effect=duplicate):
                with self.assertRaisesRegex(ValueError, 'Duplicate generated instructions'): RecipeCatalog(store).install(True)
        # Use a SQLite backup of test-owned state, never a production DB copy.
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with self.store.connect() as source, store.connect() as target: source.backup(target)
            with store.connect() as db: db.execute("UPDATE generated_recipe_packs SET definition_sha256='changed'")
            with self.assertRaisesRegex(ValueError, 'definitions differ'): RecipeCatalog(store).get('x-recipes-00000')
            with self.assertRaises(PermissionError): RecipeCatalog(store).remove()
            self.assertEqual(RecipeCatalog(store).remove(True), 100000)
            self.assertEqual(RecipeCatalog(store).status(True)['installed_profiles'], 0)

    def test_cli_status_reports_actual_installation_without_training(self):
        from agent.commands import main
        output = io.StringIO()
        with patch.dict('os.environ', {'AGENT_DATA_DIR': self.folder.name}), redirect_stdout(output):
            self.assertEqual(main(['skills', 'recipes', 'status']), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['installed_profiles'], 100000)
        self.assertFalse(report['training_performed'])

    def test_optimize_and_reset_preserve_results_history_and_other_table_statistics(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with self.store.connect() as source, store.connect() as target: source.backup(target)
            catalog = SkillCatalog(store); recipes = RecipeCatalog(store)
            before = catalog.search('Python correctness beginner')
            digest = recipes.install(True)['rendered_sha256']
            turn = store.add('preserved-session', 'Original prompt', 'Original answer', [], 'original-model')
            with store.connect() as db:
                db.execute('CREATE TABLE unrelated_analysis (id INTEGER PRIMARY KEY, label TEXT)')
                db.execute("INSERT INTO unrelated_analysis VALUES (1,'preserve')")
                db.execute('ANALYZE unrelated_analysis')
                other_stats = [tuple(row) for row in db.execute("SELECT * FROM sqlite_stat1 WHERE tbl='unrelated_analysis'")]
            with self.assertRaises(PermissionError): recipes.optimize()
            for reset in (False, True, False):
                result = recipes.optimize(True, reset)
                self.assertFalse(result['recipe_content_changed'])
                self.assertEqual(catalog.search('Python correctness beginner'), before)
                self.assertEqual(catalog.search('x-recipes-90000')['skills'], [])
                self.assertEqual(recipes.install(True)['rendered_sha256'], digest)
                with store.connect() as db:
                    self.assertEqual([tuple(row) for row in db.execute("SELECT * FROM sqlite_stat1 WHERE tbl='unrelated_analysis'")], other_stats)
                    collected = db.execute("SELECT COUNT(*) FROM sqlite_stat1 WHERE tbl='generated_recipes'").fetchone()[0]
                    self.assertEqual(collected > 0, not reset)
                    self.assertEqual(db.execute('SELECT response FROM turns WHERE id=?', (turn,)).fetchone()[0], 'Original answer')

    def test_optimize_requires_existing_pack_and_cli_routes_explicit_maintenance(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            with self.assertRaisesRegex(ValueError, 'complete matching'): RecipeCatalog(store).optimize(True)
            with store.connect() as db:
                self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_stat1'").fetchone())
        from agent.commands import main
        output = io.StringIO()
        with patch.dict('os.environ', {'AGENT_DATA_DIR': self.folder.name}), redirect_stdout(output):
            self.assertEqual(main(['skills', 'recipes', 'optimize', '--approve']), 0)
        self.assertEqual(json.loads(output.getvalue())['query_statistics'], 'collected')

    def test_real_http_activation_context_and_security_boundary(self):
        provider = Mock(); provider.generate.side_effect = lambda messages: ('Fixture answer.', messages)
        settings = replace(Settings(), data_dir=self.folder.name, provider='huggingface', api_token='')
        agent = Agent(settings, provider, store=self.store)
        client = TestClient(create_app(settings, agent), base_url='http://127.0.0.1')
        client.post('/api/account/register', json={'username':'recipe-reader','display_name':'Reader','password':'temporary test account password'}).raise_for_status()
        session = str(uuid4())
        info = client.get('/api/skills').json()
        self.assertEqual(info['extended_catalog']['generated_profiles'], 90000)
        self.assertEqual(client.get('/api/skills/profile/x-recipes-90000').status_code, 403)
        denied = client.post('/api/skills/command', json={'session_id':session,'command':'/skill x-recipes-90000'})
        self.assertEqual(denied.status_code, 403); provider.generate.assert_not_called()
        client.post('/api/skills/command', json={'session_id':session,'command':'/skill x-recipes-25000'}).raise_for_status()
        client.post('/api/chat', json={'session_id':session,'message':'Explain a small Python example.'}).raise_for_status()
        context = provider.generate.call_args.args[0][0]['content']
        self.assertIn(grammar.NOTICE, context); self.assertIn('Subject: Python', context)
        self.assertIn('Profiles grant no tools or privileges', context)
        self.assertEqual(client.get('/api/skills/current', params={'session_id':session}).json()['skill'], 'x-recipes-25000')


if __name__ == '__main__': unittest.main()
