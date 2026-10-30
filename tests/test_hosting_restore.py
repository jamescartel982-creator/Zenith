from io import BytesIO
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from cryptography.fernet import Fernet
from scripts.restore_hosting_state import restore


class HostingRestoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.destination = self.root / 'state'
        self.archive = self.root / 'state.enc'
        self.key = Fernet.generate_key()

    def bundle(self, files=None, change=None):
        files = files or {'data/account.txt': b'private fixture', 'checkpoint/weights.txt': b'fixed fixture weights'}
        manifest = {'schema_version': 1, 'files': {
            name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
            for name, value in files.items()}}
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in files.items():
                archive.writestr('profile/' + name, value)
            if change:
                change(archive, manifest)
            archive.writestr('manifest.json', json.dumps(manifest))
        encrypted = Fernet(self.key).encrypt(buffer.getvalue())
        self.archive.write_bytes(encrypted)
        return hashlib.sha256(encrypted).hexdigest()

    def test_authenticated_copy_is_private_and_does_not_change_bundle(self):
        checksum = self.bundle()
        before = self.archive.read_bytes()
        self.assertTrue(restore(self.archive, self.destination, self.key, checksum))
        self.assertEqual((self.destination / 'data/account.txt').read_bytes(), b'private fixture')
        self.assertEqual(self.archive.read_bytes(), before)
        if __import__('os').name != 'nt':
            self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
            self.assertEqual((self.destination / 'data/account.txt').stat().st_mode & 0o777, 0o600)

    def test_existing_state_is_never_overwritten(self):
        checksum = self.bundle()
        self.destination.mkdir()
        original = self.destination / 'account.txt'
        original.write_text('existing')
        self.assertFalse(restore(self.archive, self.destination, self.key, checksum))
        self.assertEqual(original.read_text(), 'existing')

    def test_destination_symlinks_are_never_followed(self):
        checksum = self.bundle()
        try:
            self.destination.symlink_to(self.root / 'absent', target_is_directory=True)
        except OSError:
            self.skipTest('Creating symbolic links requires platform permission')
        self.assertFalse(restore(self.archive, self.destination, self.key, checksum))
        self.assertFalse((self.root / 'absent').exists())

    def test_wrong_key_or_tampered_encrypted_archive_creates_no_state(self):
        checksum = self.bundle()
        with self.assertRaisesRegex(ValueError, 'authentication failed'):
            restore(self.archive, self.destination, Fernet.generate_key(), checksum)
        self.assertFalse(self.destination.exists())
        self.archive.write_bytes(self.archive.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            restore(self.archive, self.destination, self.key, checksum)
        self.assertFalse(self.destination.exists())

    def test_traversal_absolute_and_ambiguous_paths_are_rejected(self):
        for name in ['../outside', '/outside', 'folder/../../outside', 'folder//outside', 'folder\\outside', 'C:/outside']:
            with self.subTest(name=name):
                checksum = self.bundle({name: b'private'})
                with self.assertRaises(ValueError):
                    restore(self.archive, self.destination, self.key, checksum)
                self.assertFalse(self.destination.exists())
                self.assertFalse((self.root / 'outside').exists())
                self.assertEqual(list(self.root.glob('.zenith-state-*')), [])

    def test_extra_files_and_symbolic_links_are_rejected(self):
        def extra(archive, manifest):
            archive.writestr('unexpected.txt', b'private')
        checksum = self.bundle(change=extra)
        with self.assertRaises(ValueError):
            restore(self.archive, self.destination, self.key, checksum)
        def link(archive, manifest):
            name = 'link'
            info = zipfile.ZipInfo('profile/' + name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, '/outside')
            manifest['files'][name] = {'bytes': 8, 'sha256': hashlib.sha256(b'/outside').hexdigest()}
        checksum = self.bundle(change=link)
        with self.assertRaisesRegex(ValueError, 'regular files'):
            restore(self.archive, self.destination, self.key, checksum)
        self.assertFalse(self.destination.exists())

    def test_artifact_hash_mismatch_is_atomic(self):
        checksum = self.bundle(change=lambda archive, manifest: manifest['files']['data/account.txt'].update(sha256='0' * 64))
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            restore(self.archive, self.destination, self.key, checksum)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('.zenith-state-*')), [])

    def test_privileged_hosting_entrypoint_refuses_before_restoring_state(self):
        import importlib.util
        from unittest.mock import patch
        path = Path(__file__).resolve().parents[1] / 'deploy/railway/entrypoint.py'
        spec = importlib.util.spec_from_file_location('zenith_hosting_entrypoint_test', path)
        entrypoint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entrypoint)
        with patch.object(entrypoint.os, 'getuid', return_value=0, create=True), \
                patch.object(entrypoint.os, 'umask'), patch('scripts.restore_hosting_state.restore') as operation:
            with self.assertRaisesRegex(ValueError, 'without root privileges'):
                entrypoint.start()
            operation.assert_not_called()

    def test_hosted_base_cache_is_selected_on_persistent_storage(self):
        import importlib.util
        import os
        from unittest.mock import patch
        path = Path(__file__).resolve().parents[1] / 'deploy/railway/entrypoint.py'
        spec = importlib.util.spec_from_file_location('zenith_hosting_cache_test', path)
        entrypoint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entrypoint)
        with patch.dict(os.environ, {'HF_HOME': '/ephemeral/model-cache'}):
            cache = entrypoint.persistent_cache(self.root)
            self.assertEqual(cache, self.root / 'huggingface')
            self.assertTrue(cache.is_dir())
            self.assertEqual(os.environ['HF_HOME'], str(cache))
