"""Cross-platform installation, configuration, and command regression checks."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.commands import main as command_main, COMMANDS
from agent.config import Settings
from agent.doctor import inspect
from agent.models import cache_status, model_specs
from agent.paths import config_file, default_data_dir, zenith_home
from agent.setup import write_configuration

ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def test_profile_preserves_existing_configuration(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'ZENITH_HOME': folder}):
            path, created = write_configuration('local')
            self.assertTrue(created)
            self.assertIn('AI_PROVIDER=huggingface', path.read_text())
            original = path.read_bytes()
            self.assertFalse(write_configuration('ensemble')[1])
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(write_configuration('ensemble', overwrite=True)[1])
            self.assertIn('AI_PROVIDER=ensemble', path.read_text())
            self.assertNotIn('TOKEN=', path.read_text())

    def test_user_paths_are_stable_and_existing_checkout_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'ZENITH_HOME': folder}):
            self.assertEqual(zenith_home(), Path(folder).resolve())
            self.assertEqual(config_file(), Path(folder).resolve() / 'config.env')
            previous = Path.cwd()
            checkout = Path(folder) / 'checkout'; checkout.mkdir()
            profile = Path(folder).resolve() / 'profile'
            os.environ['ZENITH_HOME'] = str(profile)
            try:
                os.chdir(checkout)
                self.assertEqual(Path(default_data_dir()), profile / 'data')
                local = Path('data'); local.mkdir()
                (local / 'zenith.sqlite3').touch()
                self.assertEqual(Path(default_data_dir()), local.resolve())
            finally:
                os.chdir(previous)

    def test_profile_loads_from_other_directory_and_environment_takes_precedence(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as elsewhere:
            write_configuration('local', Path(folder) / 'config.env')
            environment = os.environ.copy()
            for key in ('AI_PROVIDER', 'AGENT_DATA_DIR', 'ZENITH_CONFIG_FILE'):
                environment.pop(key, None)
            environment.update(ZENITH_HOME=folder, PYTHONPATH=str(ROOT))
            code = 'import json; from agent.config import Settings; s=Settings(); print(json.dumps([s.provider,s.data_dir]))'
            value = json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=elsewhere, env=environment, text=True))
            self.assertEqual(value, ['huggingface', str(Path(folder).resolve() / 'data')])
            environment['AI_PROVIDER'] = 'ollama'
            value = json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=elsewhere, env=environment, text=True))
            self.assertEqual(value[0], 'ollama')

    def test_checkout_env_overrides_saved_profile(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as checkout:
            write_configuration('local', Path(folder) / 'config.env')
            (Path(checkout) / '.env').write_text('AI_PROVIDER=ollama\n', encoding='utf-8')
            environment = {**os.environ, 'ZENITH_HOME': folder, 'PYTHONPATH': str(ROOT)}
            environment.pop('AI_PROVIDER', None); environment.pop('ZENITH_CONFIG_FILE', None)
            result = subprocess.check_output([sys.executable, '-c', 'from agent.config import Settings; print(Settings().provider)'], cwd=checkout, env=environment, text=True)
            self.assertEqual(result.strip(), 'ollama')

    def test_command_dispatch_restores_process_arguments(self):
        previous = sys.argv
        module = type('Module', (), {'main': staticmethod(lambda: 7)})
        with patch('agent.commands.importlib.import_module', return_value=module) as imported:
            self.assertEqual(command_main(['catalog', '--validate']), 7)
            imported.assert_called_once_with('scripts.catalog')
        self.assertIs(sys.argv, previous)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(command_main(['unknown-command']), 2)

    def test_all_command_help_works_without_model_download(self):
        for name in COMMANDS:
            with self.subTest(command=name):
                result = subprocess.run([sys.executable, '-m', 'agent', name, '--help'], cwd=ROOT,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout.lower())

    def test_bootstrap_forwards_paths_and_keeps_ollama_lightweight(self):
        spec = importlib.util.spec_from_file_location('zenith_bootstrap_test', ROOT / 'install.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='zenith install spaces ') as folder:
            target = Path(folder).resolve() / '.venv'
            with patch.object(module.venv.EnvBuilder, 'create') as create, patch.object(module, 'run') as run, patch.object(module, 'configured_provider', return_value='ollama'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--mode', 'ollama', '--venv', str(target)]), 0)
                create.assert_called_once_with(target)
                commands = [list(map(str, call.args[0])) for call in run.call_args_list]
                self.assertTrue(all(command[0] == str(module.environment_python(target)) for command in commands))
                self.assertFalse(any('download.pytorch.org' in str(command) for command in commands))
                self.assertTrue(any('configure' in command and 'ollama' in command for command in commands))
                self.assertFalse(any('download' in command for command in commands))

    def test_bootstrap_failures_return_nonzero_without_deleting_an_environment(self):
        spec = importlib.util.spec_from_file_location('zenith_bootstrap_fail_test', ROOT / 'install.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder, patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run', side_effect=subprocess.CalledProcessError(1, ['pip'])):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--venv', folder]), 1)
            self.assertTrue(Path(folder).is_dir())

    def test_model_cache_checks_shards_and_missing_tokenizers_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            spec = {'provider': 'huggingface', 'model': folder, 'revision': 'main'}
            self.assertFalse(cache_status(spec)['cached'])
            for name in ['config.json', 'tokenizer_config.json', 'tokenizer.json']:
                (path / name).write_text('{}')
            (path / 'model.safetensors.index.json').write_text(json.dumps({'weight_map': {'a': 'first.safetensors', 'b': 'second.safetensors'}}))
            (path / 'first.safetensors').write_bytes(b'fixture')
            self.assertFalse(cache_status(spec)['cached'])
            (path / 'second.safetensors').write_bytes(b'fixture')
            self.assertTrue(cache_status(spec)['cached'])

    def test_diagnostics_do_not_run_inference_or_expose_tokens_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(provider='ollama', data_dir=folder, api_token='fixture-private-token')
            with patch('requests.get', side_effect=OSError), patch('agent.providers.make_provider') as generate:
                report = inspect(settings)
            generate.assert_not_called()
            self.assertTrue(report['ok'])
            self.assertFalse(report['inference_tested'])
            self.assertNotIn(settings.api_token, json.dumps(report))
            self.assertTrue(any(check['name'] == 'ollama' and check['status'] == 'warning' for check in report['checks']))

    def test_bad_cli_answer_needs_correction_before_approval(self):
        from agent import cli
        from agent.core import Agent
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(provider='huggingface', data_dir=folder)
            provider = type('Provider', (), {'generate': lambda self, messages: ('Incorrect', messages)})()
            agent = Agent(settings, provider=provider)
            answers = iter(['Question', '/bad', '/approve', '/quit'])
            with patch('agent.cli.Agent', return_value=agent), patch('builtins.input', side_effect=lambda _: next(answers)), patch.object(sys, 'argv', ['zenith chat']), contextlib.redirect_stdout(io.StringIO()) as output:
                cli.main()
            self.assertEqual(agent.store.approved_examples(), [])
            self.assertIn('corrected response', output.getvalue())
