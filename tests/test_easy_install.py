"""Installation-to-launch flow and browser startup ownership."""
import contextlib
import importlib.util
import io
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.browser import open_when_ready

ROOT = Path(__file__).resolve().parents[1]


def bootstrap():
    spec = importlib.util.spec_from_file_location('zenith_easy_bootstrap', ROOT / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Flow tests mock package installation; platform wheel support is tested
    # separately in test_macos_install, including explicit Intel rejection.
    module.platform = SimpleNamespace(system=lambda: 'Linux', machine=lambda: 'x86_64',
                                      mac_ver=lambda: ('', (), ''))
    return module


class EasyInstallTests(unittest.TestCase):
    def test_experimental_candidate_selection_is_explicit_and_precedes_launch(self):
        module=bootstrap()
        with tempfile.TemporaryDirectory(prefix='zenith candidate spaces ') as folder:
            with patch.object(module.venv.EnvBuilder,'create'),patch.object(module,'run') as run,patch.object(module,'configured_provider',return_value='huggingface'),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--venv',folder,'--launch','--activate-candidate']),0)
                commands=[list(map(str,c.args[0])) for c in run.call_args_list]
                selected=next(i for i,c in enumerate(commands) if 'setup' in c and '--activate-candidate' in c)
                self.assertLess(selected,len(commands)-1)
                self.assertFalse(any(c[-2:]==['models','download'] for c in commands))

    def test_candidate_installer_can_switch_from_an_external_runtime_without_erasing_settings(self):
        module=bootstrap()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(module.venv.EnvBuilder,'create'),patch.object(module,'run') as run,patch.object(module,'configured_provider',return_value='ollama'),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--venv',folder,'--activate-candidate']),0)
                commands=[list(map(str,c.args[0])) for c in run.call_args_list]
                self.assertTrue(any('torch>=2.6,<3' in c for c in commands))
                self.assertTrue(any('setup' in c and '--activate-candidate' in c for c in commands))
                self.assertFalse(any('--overwrite' in c for c in commands))

    def test_explicit_release_is_cached_and_activated_before_launch(self):
        module=bootstrap()
        with tempfile.TemporaryDirectory(prefix='zenith release spaces ') as folder:
            with patch.object(module.venv.EnvBuilder,'create'),patch.object(module,'run') as run,patch.object(module,'configured_provider',return_value='huggingface'),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--venv',folder,'--launch','--activate-release',folder]),0)
                commands=[list(map(str,call.args[0])) for call in run.call_args_list]
                activation=next(i for i,c in enumerate(commands) if 'use-release' in c)
                self.assertLess(activation,len(commands)-1)
                self.assertIn('--approve',commands[activation])
                self.assertIn('--download-base',commands[activation])
                self.assertFalse(any(c[-2:]==['models','download'] for c in commands))
            with patch.object(module.venv.EnvBuilder,'create'),patch.object(module,'run') as run,patch.object(module,'configured_provider',return_value='ollama'),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--venv',folder,'--activate-release',folder]),1)
                self.assertFalse(any('use-release' in call.args[0] for call in run.call_args_list))

    def test_launch_downloads_before_serving_and_uses_selected_environment(self):
        module = bootstrap()
        with tempfile.TemporaryDirectory(prefix='zenith launch spaces ') as folder:
            with patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run') as run, patch.object(module, 'configured_provider', return_value='huggingface'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--venv', folder, '--launch']), 0)
                commands = [list(map(str, call.args[0])) for call in run.call_args_list]
                self.assertTrue(all(c[0] == str(module.environment_python(Path(folder).resolve())) for c in commands))
                download = next(i for i, c in enumerate(commands) if c[-2:] == ['models', 'download'])
                self.assertLess(download, len(commands) - 1)
                self.assertEqual(commands[-1][1:], ['-m', 'agent', 'serve', '--open-browser'])

    def test_setup_failure_never_launches_and_interrupt_is_actionable(self):
        module = bootstrap()
        for error, code in [(subprocess.CalledProcessError(1, ['pip']), 1), (KeyboardInterrupt(), 130)]:
            with tempfile.TemporaryDirectory() as folder, patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run', side_effect=error) as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--venv', folder, '--launch']), code)
                self.assertEqual(run.call_count, 1)

    def test_external_runtime_launch_stays_lightweight_and_preserves_start_failure(self):
        module = bootstrap()
        def run(command, environment=None):
            if 'serve' in command:
                raise subprocess.CalledProcessError(7, command)
        with tempfile.TemporaryDirectory() as folder, patch.object(module.venv.EnvBuilder, 'create'), patch.object(module, 'run', side_effect=run) as calls, patch.object(module, 'configured_provider', return_value='ollama'), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(module.main(['--venv', folder, '--launch']), 7)
            self.assertIn('installed, but could not start', output.getvalue())
            commands = [list(map(str, c.args[0])) for c in calls.call_args_list]
            self.assertFalse(any('download' in c for c in commands))
            self.assertFalse(any('download.pytorch.org' in str(c) for c in commands))

    def test_browser_waits_for_this_server_and_never_opens_on_failure(self):
        server = SimpleNamespace(started=False)
        stopped = Event()
        with patch('agent.browser.webbrowser.open') as browser:
            stopped.set()
            open_when_ready(server, 'http://127.0.0.1:7860', stopped)
            browser.assert_not_called()
        stopped.clear()
        with patch.object(stopped, 'wait', side_effect=lambda _: setattr(server, 'started', True)), patch('agent.browser.webbrowser.open', return_value=True) as browser:
            open_when_ready(server, 'http://127.0.0.1:7860', stopped)
            browser.assert_called_once_with('http://127.0.0.1:7860')

    def test_browser_unavailable_shows_url_and_timeout_does_not_open(self):
        with patch('agent.browser.webbrowser.open', return_value=False) as browser, contextlib.redirect_stdout(io.StringIO()) as output:
            open_when_ready(SimpleNamespace(started=True), 'http://127.0.0.1:8000', Event())
            self.assertIn('http://127.0.0.1:8000', output.getvalue())
            browser.assert_called_once()
        with patch('agent.browser.webbrowser.open') as browser, contextlib.redirect_stdout(io.StringIO()):
            open_when_ready(SimpleNamespace(started=False), 'http://127.0.0.1:8000', Event(), timeout=0)
            browser.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'Linux launcher contract')
    def test_linux_start_uses_checkout_environment_from_another_directory(self):
        with tempfile.TemporaryDirectory(prefix='zenith easy spaces ') as folder, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(folder)
            for name in ['start.sh', 'run.sh']:
                (root / name).write_bytes((ROOT / name).read_bytes())
            python = root / '.venv/bin/python'; python.parent.mkdir(parents=True)
            code = 'import sys,json; print(json.dumps(sys.argv[1:]))'
            python.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote(code) + ' \"$@\"\n')
            python.chmod(0o755)
            result = subprocess.run(['bash', str(root / 'start.sh'), '--port', '8123'], cwd=elsewhere, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), ['-m', 'agent', 'serve', '--open-browser', '--port', '8123'])

    @unittest.skipUnless(os.name == 'nt', 'Windows CMD launchers')
    def test_windows_double_click_launchers_forward_help_without_installing(self):
        environment = {**os.environ, 'ZENITH_NO_PAUSE':'1'}
        for name in ['Install Zenith.cmd', 'Start Zenith.cmd']:
            if name.startswith('Start') and not (ROOT / '.venv/Scripts/python.exe').is_file():
                continue
            with self.subTest(launcher=name):
                result = subprocess.run([str(ROOT / name), '--help'], cwd=ROOT.parent, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn('usage:', result.stdout.lower())
