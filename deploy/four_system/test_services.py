"""Actual unit serialization and systemd parser checks; never start runtime services."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('services', Path(__file__).with_name('services.py'))
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='zenith-services-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan = {'schema_version': 1, 'services': {}}
        for role in services.ROLES:
            env = self.root / (role + '.env')
            env.write_text('')
            env.chmod(0o600)
            self.plan['services'][role] = {
                'command': [str(Path(sys.executable).resolve()), '-c', 'pass'],
                'working_directory': str(self.root), 'environment_file': str(env),
                'memory_max_mb': 512, 'tasks_max': 128,
                'after': ['inference'] if role in {'hermes', 'openclaw', 'tradingagents'} else [],
            }

    def test_all_components_and_periodic_liveness_are_connected(self):
        units = services.units(self.plan)
        self.assertEqual(len(units), 9)
        for role in services.ROLES:
            name = 'zenith-' + role + '.service'
            self.assertIn(name, units[services.TARGET])
            self.assertIn('PartOf=zenith-platform.target', units[name])
            self.assertIn('Restart=always', units[name])
            self.assertIn('NoNewPrivileges=yes', units[name])
            self.assertIn('UMask=0077', units[name])
            self.assertNotIn('User=root', units[name])
        self.assertIn('zenith-platform-health.timer', units[services.TARGET])
        self.assertNotIn('zenith-platform-health.service', units[services.TARGET])
        self.assertIn('OnUnitActiveSec=1min', units['zenith-platform-health.timer'])

    def test_literal_arguments_do_not_expand_credentials_or_specifiers(self):
        value = '$HOME %u "quoted" \\tail'
        self.assertEqual(services.quote(value, True), '"$$HOME %%u \\"quoted\\" \\\\tail"')
        self.assertEqual(services.quote('/state/$literal'), '"/state/$literal"')
        for invalid in ['line\nbreak', 'carriage\rreturn', '\0nul', '', 42]:
            with self.assertRaises(ValueError):
                services.quote(invalid)

    def test_rejects_missing_roles_cycles_and_command_injection(self):
        invalid = []
        changed = copy.deepcopy(self.plan);changed['services'].pop('bridge');invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['inference']['after'] = ['hermes'];invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['bridge']['after'] = [{}];invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['bridge']['command'] = 'python; sh';invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['bridge']['command'][0] = 'python';invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['bridge']['memory_max_mb'] = True;invalid.append(changed)
        changed = copy.deepcopy(self.plan);changed['services']['bridge']['working_directory'] += '\nExecStart=sh';invalid.append(changed)
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                services.validate(plan)

    def test_rejects_shared_or_public_environment_files(self):
        changed = copy.deepcopy(self.plan)
        changed['services']['hermes']['environment_file'] = changed['services']['openclaw']['environment_file']
        with self.assertRaises(ValueError):services.validate(changed)
        secret = Path(self.plan['services']['hermes']['environment_file'])
        secret.chmod(0o644)
        with self.assertRaises(ValueError):services.validate(self.plan)
        secret.chmod(0o600)
        alias = self.root / 'linked.env';alias.symlink_to(secret)
        self.plan['services']['hermes']['environment_file'] = str(alias)
        with self.assertRaises(ValueError):services.validate(self.plan)

    def test_install_never_overwrites_files_or_reads_environment_values(self):
        secret = Path(self.plan['services']['hermes']['environment_file'])
        secret.write_text('API_SECRET=private-test-value\n')
        output = self.root / 'units'
        names = services.write_units(self.plan, output)
        before = {name:(output/name).read_bytes() for name in names}
        self.assertFalse(any(b'private-test-value' in content for content in before.values()))
        self.assertTrue(all((output/name).stat().st_mode & 0o777 == 0o600 for name in names))
        with self.assertRaises(ValueError):services.write_units(self.plan, output)
        self.assertEqual(before, {name:(output/name).read_bytes() for name in names})

    def test_bad_output_directory_and_failed_writes_leave_no_partial_units(self):
        output = self.root / 'units'
        output.mkdir()
        alias = self.root / 'alias';alias.symlink_to(output, target_is_directory=True)
        with self.assertRaises(ValueError):services.write_units(self.plan, alias)
        real_open = os.open
        calls = 0
        def fail_second(path, *args):
            nonlocal calls
            calls += 1
            if calls == 2:raise OSError('simulated full disk')
            return real_open(path, *args)
        with patch.object(services.os, 'open', side_effect=fail_second), self.assertRaises(OSError):
            services.write_units(self.plan, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_cli_render_and_invalid_install_have_no_service_effects(self):
        plan = self.root / 'plan.json';plan.write_text(json.dumps(self.plan))
        output = self.root / 'preview'
        with patch.object(services.subprocess, 'run') as run:
            self.assertEqual(services.main(['render','--plan',str(plan),'--directory',str(output)]),0)
            run.assert_not_called()
            other = self.root / 'invalid-install'
            self.assertEqual(services.main(['install','--plan',str(plan),'--directory',str(other)]),1)
            self.assertFalse(other.exists())
            run.assert_not_called()

    def test_install_activation_checks_each_process_without_claiming_readiness(self):
        plan = self.root / 'plan.json';plan.write_text(json.dumps(self.plan))
        with patch.object(services.Path, 'home', return_value=self.root), patch.object(services.subprocess, 'run') as run:
            self.assertEqual(services.main(['install','--plan',str(plan),'--start']),0)
            self.assertEqual(run.call_count,3)
            self.assertEqual(run.call_args_list[0].args[0],['systemctl','--user','daemon-reload'])
            self.assertEqual(run.call_args_list[1].args[0],['systemctl','--user','enable','--now',services.TARGET])
            self.assertEqual(set(run.call_args_list[2].args[0][4:]),{'zenith-'+role+'.service' for role in services.ROLES})

    def test_startup_liveness_failure_is_reported_as_failure(self):
        plan = self.root / 'plan.json';plan.write_text(json.dumps(self.plan))
        failure = subprocess.CalledProcessError(3,['systemctl','--user','is-active'])
        with patch.object(services.Path, 'home', return_value=self.root), patch.object(services.subprocess, 'run', side_effect=[None,None,failure]):
            self.assertEqual(services.main(['install','--plan',str(plan),'--start']),1)

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'Requires native Linux systemd parser')
    def test_native_systemd_parser_accepts_all_generated_units(self):
        output = self.root / 'units';names = services.write_units(self.plan, output)
        result = subprocess.run(['systemd-analyze','verify', *[str(output/name) for name in names]],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':unittest.main()
