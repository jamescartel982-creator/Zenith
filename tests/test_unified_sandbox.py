"""Policy/permission regressions; live container verification is a separate smoke."""
import json
import os
import subprocess
import unittest
from unittest.mock import Mock, patch

from agent.sandbox import SandboxPolicy, run_python, validate_program
from agent.sandbox_docker import DockerSandbox, SandboxUnavailable
from agent.tool_protocol import ToolCall

IMAGE = 'sha256:' + 'a'*64


class SandboxPolicyTests(unittest.TestCase):
    def test_default_off_cannot_launch_backend(self):
        with patch.dict(os.environ, {'ZENITH_SANDBOX_ENABLED': 'false'}), patch('agent.sandbox_docker.DockerSandbox') as backend:
            with self.assertRaises(PermissionError): run_python({'source': 'print(1)'}, lambda: None)
        backend.assert_not_called()

    def test_concurrent_owner_calls_cannot_multiply_container_resources(self):
        from agent.sandbox import _SLOTS
        self.assertTrue(_SLOTS.acquire(blocking=False))
        try:
            with patch.dict(os.environ, {'ZENITH_SANDBOX_ENABLED': 'true', 'ZENITH_SANDBOX_IMAGE': IMAGE}), patch('agent.sandbox_docker.DockerSandbox') as backend:
                with self.assertRaisesRegex(ValueError, 'slot is busy'):
                    run_python({'source': 'print(1)'}, lambda: None)
                backend.assert_not_called()
        finally: _SLOTS.release()

    def test_missing_authority_stops_before_backend_or_program(self):
        authority = Mock(side_effect=PermissionError('revoked'))
        with patch('agent.sandbox_docker.DockerSandbox') as backend:
            with self.assertRaises(PermissionError): run_python({'source': 'print(1)'}, authority)
        backend.assert_not_called()

    def test_host_controls_cannot_be_supplied_by_tool_arguments(self):
        for arguments in [{'source': 'x', 'mount': '/home'}, {'source': 'x', 'network': 'host'},
                          {'source': 'x', 'image': IMAGE}, {'command': 'sh'}, {'source': '\0'},
                          {'source': 'é'*4097}]:
            with self.subTest(arguments=list(arguments)):
                with self.assertRaises(ValueError): ToolCall.parse({'tool': 'sandbox-python', 'arguments': arguments})
        call = ToolCall.parse({'tool': 'sandbox-python', 'arguments': {'source': 'print(1)'}})
        changed = call.arguments; changed['source'] = 'print(2)'
        self.assertEqual(call.arguments['source'], 'print(1)')

    def test_configuration_requires_local_image_pin_and_bounded_resources(self):
        for kw in [{'enabled': True}, {'enabled': True, 'image': 'python:latest'},
                   {'seconds': 31}, {'seconds': True}, {'output_bytes': 999999}]:
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError): SandboxPolicy(**kw)
        with patch.dict(os.environ, {'ZENITH_SANDBOX_ENABLED': 'maybe'}):
            with self.assertRaises(ValueError): SandboxPolicy.from_env()

    def test_missing_docker_does_not_execute_on_host(self):
        with patch('agent.sandbox_docker.shutil.which', return_value=None), patch('agent.sandbox_docker.subprocess.run') as run:
            sandbox = DockerSandbox(SandboxPolicy(True, IMAGE))
            with self.assertRaises(SandboxUnavailable): sandbox.run('print(1)', lambda: None)
        run.assert_not_called()

    def test_unreviewed_image_or_declared_volume_is_rejected(self):
        sandbox = DockerSandbox(SandboxPolicy(True, IMAGE))
        for config in [{'Env': ['API_SECRET=canary-private']}, {'Volumes': {'/host': {}}}]:
            responses = [b'linux\n', b'2 true true true', json.dumps(['name=seccomp,profile=builtin']).encode(),
                         json.dumps([{'Id': IMAGE, 'Os': 'linux', 'Config': config}]).encode()]
            with patch.object(sandbox, '_control', side_effect=responses):
                with self.assertRaises(SandboxUnavailable): sandbox._preflight()

    def test_daemon_without_builtin_seccomp_is_rejected(self):
        sandbox = DockerSandbox(SandboxPolicy(True, IMAGE))
        with patch.object(sandbox, '_control', side_effect=[b'linux', b'2 true true true', b'[]']):
            with self.assertRaises(SandboxUnavailable): sandbox._preflight()

    def test_docker_errors_do_not_disclose_private_configuration(self):
        result = subprocess.CompletedProcess([], 1, stdout=b'', stderr=b'canary-private-token')
        with patch('agent.sandbox_docker.subprocess.run', return_value=result):
            sandbox = DockerSandbox(SandboxPolicy(True, IMAGE))
            with self.assertRaises(SandboxUnavailable) as caught: sandbox._control('info')
        self.assertNotIn('canary-private', str(caught.exception))
