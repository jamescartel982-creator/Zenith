"""Opt-in policy, source integrity, exact context and tool-activation regressions."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from zenith_integrations.hermes.compatibility import verify_manifest

TEMPLATE=Path(__file__).resolve().parents[3]/'integrations/hermes_compat/zenith_chat_compat.py'


def fixture(root):
    paths=['agent/agent_init.py','gateway/platforms/api_server.py','gateway/run_turn_runner.py','zenith_chat_compat.py']
    for path in paths:
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(TEMPLATE.read_text() if path=='zenith_chat_compat.py' else '# integrity fixture\n')
    definition={'policy':'zenith-chat-only-v1','source_pin':'d05095663342556788cf2a198bfa7844cc7968ab','files':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}}
    digest=hashlib.sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest=root/'zenith-compat-build.json';manifest.write_text(json.dumps({'schema_version':1,'definition':definition,'build_sha256':digest}));manifest.chmod(0o600)
    spec=importlib.util.spec_from_file_location('fixture_compatibility',root/'zenith_chat_compat.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return manifest,module,digest


class CompatibilityTests(unittest.TestCase):
    def test_default_is_off_and_enabled_chat_guard_refuses_other_execution_surfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest,module,digest=fixture(root)
            self.assertEqual(verify_manifest(manifest),digest)
            args={'model':'zenith','provider':'custom','platform':'api_server','base_url':'http://127.0.0.1:8781/v1','_config_context_length':8192,'enabled_toolsets':[],'tools':[]}
            agent=SimpleNamespace(**args)
            with patch.dict(os.environ,{'ZENITH_HERMES_CHAT_ONLY':'0','ZENITH_HERMES_PROFILE_ID':'profile'}):self.assertFalse(module.allow_small_context(agent,8192))
            with patch.dict(os.environ,{'ZENITH_HERMES_CHAT_ONLY':'1','ZENITH_HERMES_PROFILE_ID':'profile'}):
                self.assertTrue(module.allow_small_context(agent,8192))
                agent.context_compressor=SimpleNamespace(context_length=8192)
                captured={'usage':{'input_tokens':10}}
                module.record_served_runtime(agent,{'final_response':'4'},captured)
                self.assertEqual(captured['usage']['runtime'],{'provider':'custom','model':'zenith'})
                other=SimpleNamespace(**(args|{'model':'other'}),context_compressor=SimpleNamespace(context_length=8192))
                unchanged={'usage':{}};module.record_served_runtime(other,{},unchanged)
                self.assertNotIn('runtime',unchanged['usage'])
                for overrides in ({'model':'other'},{'provider':'hosted'},{'platform':'cli'},{'enabled_toolsets':None},{'enabled_toolsets':['terminal']},{'tools':[{'name':'terminal'}]},{'base_url':'https://remote.example/v1'},{'_config_context_length':16384}):
                    with self.subTest(overrides=overrides):self.assertFalse(module.allow_small_context(SimpleNamespace(**(args|overrides)),8192))
                for window in (True,0,3999,32769,64000):self.assertFalse(module.selected_window('zenith','custom','api_server',args['base_url'],window,[],[]))
                (root/'agent/agent_init.py').write_text('# changed source\n')
                self.assertFalse(module.allow_small_context(agent,8192))
                with self.assertRaises(ValueError):verify_manifest(manifest)

    def test_builder_refuses_output_alias_inside_the_original_source(self):
        path=TEMPLATE.with_name('build.py');spec=importlib.util.spec_from_file_location('compat_builder',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();(source/'original').write_text('unchanged')
            with self.assertRaises(ValueError):module.build(source,root/'alias'/'..'/'source'/'new')
            self.assertEqual((source/'original').read_text(),'unchanged')
            self.assertFalse((source/'new').exists())

    def test_forged_manifest_is_not_a_verified_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path,module,digest=fixture(Path(directory));record=json.loads(path.read_text());record['definition']['policy']='unrestricted';path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):verify_manifest(path)
            self.assertIsNone(module.verified_build())
