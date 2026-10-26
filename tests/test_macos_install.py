"""Platform wheel selection and preservation of configured native backends."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_easy_install import bootstrap


class MacInstallTests(unittest.TestCase):
    def test_secure_native_wheels_use_pypi_on_apple_silicon(self):
        module = bootstrap()
        with patch.object(module.platform, 'system', return_value='Darwin'), patch.object(module.platform, 'machine', return_value='arm64'), patch.object(module.platform, 'mac_ver', return_value=('14.7', (), '')):
            command = module.torch_install_command('native python')
        self.assertEqual(command, ['native python', '-m', 'pip', 'install', 'torch>=2.6,<3'])
        with patch.object(module.platform, 'system', return_value='Linux'):
            self.assertIn('https://download.pytorch.org/whl/cpu', module.torch_install_command('python'))

    def test_intel_rosetta_and_old_macos_never_downgrade(self):
        module = bootstrap()
        for machine, version in [('x86_64', '15.0'), ('arm64', '13.6')]:
            with self.subTest(machine=machine, version=version), patch.object(module.platform, 'system', return_value='Darwin'), patch.object(module.platform, 'machine', return_value=machine), patch.object(module.platform, 'mac_ver', return_value=(version, (), '')):
                with self.assertRaises(module.UnsupportedRuntimeError):
                    module.torch_install_command('python')

    def test_fresh_intel_native_install_rejects_before_creating_or_configuring(self):
        module = bootstrap()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'ZENITH_HOME': folder}, clear=True), patch.object(module.platform, 'system', return_value='Darwin'), patch.object(module.platform, 'machine', return_value='x86_64'), patch.object(module.venv.EnvBuilder, 'create') as create, patch.object(module, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                module.main(['--venv', str(Path(folder) / 'env')])
            self.assertEqual(result.exception.code, 2)
            create.assert_not_called()
            run.assert_not_called()
            self.assertFalse((Path(folder) / 'config.env').exists())

    def test_external_only_reasoning_profile_stays_light_on_intel(self):
        module = bootstrap()
        for provider in ['orchestrated', 'reasoning']:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as folder, patch.object(module.platform, 'system', return_value='Darwin'), patch.object(module.platform, 'machine', return_value='x86_64'), patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run') as run, patch.object(module, 'configured_provider', return_value=provider), patch.object(module, 'configured_needs_hf', return_value=False), patch.object(module, 'configured_needs_torch', return_value=False), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--mode', 'localserver', '--venv', folder]), 0)
                commands = [list(map(str, c.args[0])) for c in run.call_args_list]
                self.assertFalse(any('torch>=2.6,<3' in c for c in commands))
                self.assertFalse(any('--overwrite' in c for c in commands))

    def test_composite_tiny_auto_runtime_gets_torch(self):
        module = bootstrap()
        with tempfile.TemporaryDirectory() as folder, patch.object(module.platform, 'system', return_value='Linux'), patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run') as run, patch.object(module, 'configured_provider', return_value='ensemble'), patch.object(module, 'configured_needs_hf', return_value=False), patch.object(module, 'configured_needs_torch', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--mode', 'ollama', '--runtime', 'auto', '--venv', folder]), 0)
            self.assertTrue(any('torch>=2.6,<3' in c.args[0] for c in run.call_args_list))

    @unittest.skipIf(os.name == 'nt', 'POSIX .command launchers')
    def test_mac_launchers_support_help_from_another_directory(self):
        import subprocess
        for name in ['Install Zenith.command', 'Start Zenith.command']:
            result = subprocess.run(['bash', str(Path(__file__).resolve().parents[1] / name), '--help'], cwd=tempfile.gettempdir(), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('usage:', result.stdout.lower())
