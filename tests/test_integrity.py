import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from agent import __version__
from agent.integrity import file_digest,verify_source,verify_installed,safe_source_path,MANIFEST_NAME
from agent.config import Settings
from agent.doctor import inspect


class IntegrityTests(unittest.TestCase):
    def test_source_detects_changed_missing_and_unsafe_entries_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            names=['agent/__init__.py','README.md','LICENSE','pyproject.toml','install.py','install.sh','install.ps1','run.sh','run.ps1']
            rows=[]
            for name in names:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'fixture\n')
                rows.append({'path':name,'size':target.stat().st_size,'sha256':file_digest(target).hex(),'normalization':'lf'})
            manifest={'schema_version':1,'version':__version__,'files':rows};path=root/MANIFEST_NAME
            path.write_text(json.dumps(manifest));self.assertTrue(verify_source(root)['ok'])
            (root/'run.ps1').write_bytes(b'fixture\r\n');self.assertTrue(verify_source(root)['ok'])
            (root/'README.md').write_text('changed');(root/'LICENSE').unlink()
            errors=verify_source(root)['errors'];self.assertIn('Modified: README.md',errors);self.assertIn('Missing: LICENSE',errors)
            manifest['files'][0]['path']='../outside';path.write_text(json.dumps(manifest))
            self.assertFalse(verify_source(root)['ok'])
            for name in ['/outside','../outside','C:/outside','a\\b']:
                with self.subTest(name=name),self.assertRaises(ValueError):safe_source_path(root,name)

    def test_source_rejects_omitted_required_files_duplicate_entries_and_malformed_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'example').write_text('data')
            row={'path':'example','size':4,'sha256':hashlib.sha256(b'data').hexdigest()}
            for data in [{'schema_version':1,'version':__version__,'files':[row]},
                         {'schema_version':1,'version':__version__,'files':[row,row]}, {'files':[]}]:
                (root/MANIFEST_NAME).write_text(json.dumps(data));self.assertFalse(verify_source(root)['ok'])

    def test_source_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory,tempfile.TemporaryDirectory() as elsewhere:
            root=Path(directory).resolve();outside=Path(elsewhere)/'private';outside.write_text('private fixture')
            try:(root/'escape').symlink_to(outside)
            except OSError:self.skipTest('Symlinks require additional privileges on this platform')
            with self.assertRaises(ValueError):safe_source_path(root,'escape')

    def test_wheel_verification_detects_tampering_and_editable_installations(self):
        import base64
        import agent.integrity
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'agent').mkdir();target=root/'agent/__init__.py';target.write_bytes(b'code\n')
            item=type('WheelEntry',(),{'__str__':lambda self:'agent/__init__.py'})()
            item.hash=SimpleNamespace(mode='sha256',value=base64.urlsafe_b64encode(file_digest(target)).decode().rstrip('='));item.size=5
            dist=Mock();dist.version=__version__;dist.read_text.return_value='{}';dist.files=[item]
            dist.locate_file.side_effect=lambda name:target if name is item else root/str(name)
            with patch.object(agent.integrity,'__file__',str(root/'agent/integrity.py')):
                self.assertTrue(verify_installed(dist)['ok'])
                target.write_bytes(b'bad!\n');self.assertFalse(verify_installed(dist)['ok'])
                target.write_bytes(b'code\n');item.hash=None;self.assertFalse(verify_installed(dist)['ok'])
            dist.read_text.return_value='{"dir_info":{"editable":true}}'
            self.assertIn('Editable',verify_installed(dist)['errors'][0])

    def test_fast_doctor_executes_one_model_and_does_not_require_unused_reviewer_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=Settings(provider='ensemble',data_dir=directory,response_mode='fast')
            provider=Mock();provider.generate_fast.return_value=('4',[]);provider.last_deliberation=None
            def cached(spec):return {'cached':spec['id']=='primary','reason':'fixture'}
            with patch('agent.doctor.cache_status',side_effect=cached),patch('agent.providers.make_provider',return_value=provider),patch('agent.doctor.importlib.metadata.version',return_value='fixture'):
                value=inspect(settings,inference=True)
            self.assertTrue(value['ok']);provider.generate_fast.assert_called_once();provider.generate.assert_not_called()
            provider.reset_mock()
            with patch('agent.doctor.cache_status',side_effect=cached),patch('agent.providers.make_provider',return_value=provider),patch('agent.doctor.importlib.metadata.version',return_value='fixture'):
                value=inspect(Settings(provider='ensemble',data_dir=directory,response_mode='thorough'),inference=True)
            self.assertFalse(value['ok']);provider.generate.assert_not_called()


if __name__=='__main__':unittest.main()
