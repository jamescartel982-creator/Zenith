"""Exercise first installation, safe retries, and hostile or corrupt source archives."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('zenith_quickstart',ROOT/'quickstart.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)


def source_fixture(root):
    root.mkdir();rows=[]
    for name in sorted(bootstrap.REQUIRED):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture\n')
        rows.append({'path':name,'size':8,'sha256':hashlib.sha256(b'fixture\n').hexdigest(),'normalization':'lf'})
    (root/'release-manifest.json').write_text(json.dumps({'schema_version':1,'version':'0.14.1','files':rows}))


class QuickstartTests(unittest.TestCase):
    def test_first_download_is_verified_before_install_and_retries_reuse_files(self):
        with tempfile.TemporaryDirectory(prefix='zenith quickstart spaces ') as folder:
            root=Path(folder);source=root/'source';source_fixture(source);archive=root/'fixture.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for p in source.rglob('*'):
                    if p.is_file():z.write(p,'Zenith-main/'+p.relative_to(source).as_posix())
            target=root/'installed Zenith'
            def download(path,ref):shutil.copyfile(archive,path)
            with patch.object(bootstrap,'download_archive',side_effect=download) as fetch,patch.object(bootstrap.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(bootstrap.main(['--directory',str(target),'--activate-candidate','--no-launch']),0)
                command=run.call_args.args[0]
                self.assertEqual(command[:2],[sys.executable,str(target.resolve()/'install.py')])
                self.assertIn('--activate-candidate',command);self.assertIn('--download',command)
                (target/'private-settings.txt').write_text('user-owned fixture')
                self.assertEqual(bootstrap.main(['--directory',str(target)]),0)
                self.assertEqual(fetch.call_count,1);self.assertIn('--launch',run.call_args.args[0])
                self.assertEqual((target/'private-settings.txt').read_text(),'user-owned fixture')

    def test_modified_existing_checkout_never_runs_or_overwrites_the_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'source';source_fixture(root);(root/'install.py').write_text('user modification')
            with patch.object(bootstrap.subprocess,'run') as run,contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bootstrap.main(['--directory',str(root)]),1)
                run.assert_not_called();self.assertEqual((root/'install.py').read_text(),'user modification')

    def test_unsafe_archives_and_bad_checksums_never_publish_a_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for number,name in enumerate(['Zenith-main/../../escape','/absolute','Zenith-main/C:/escape','Zenith-main/evil\\path','./','Zenith-main/.. /escape','Zenith-main/NUL.txt']):
                archive=root/('unsafe'+str(number)+'.zip')
                with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'invalid')
                with self.subTest(path=name),self.assertRaises(ValueError):bootstrap.extract_archive(archive,root/('stage'+str(number)))
            source=root/'source';source_fixture(source);(source/'install.py').write_text('corrupt')
            archive=root/'bad-checksum.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for p in source.rglob('*'):
                    if p.is_file():z.write(p,'Zenith-main/'+p.relative_to(source).as_posix())
            with patch.object(bootstrap,'download_archive',side_effect=lambda path,ref:shutil.copyfile(archive,path)):
                with self.assertRaises(ValueError):bootstrap.prepare_source(root/'destination')
            self.assertFalse((root/'destination').exists());self.assertFalse((root/'escape').exists())

    def test_remote_script_supports_stdin_execution_without_project_dependencies(self):
        result=subprocess.run([sys.executable,'-I','-','--help'],input=(ROOT/'quickstart.py').read_text(),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--activate-candidate',result.stdout)
