import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from agent.packs import manifests, summaries, select_files, destination, verify_file, download_file
from agent.config import Settings
from agent.providers import LocalServerProvider


class PackTests(unittest.TestCase):
    def test_complete_unique_pinned_file_inventories(self):
        packs = manifests()
        self.assertEqual({p['id']: p['file_count'] for p in packs}, {'zenith-27b':33, 'zenith-vision':84, 'zenith-9b':15})
        for pack in packs:
            self.assertEqual(len(pack['revision']), 40)
            self.assertEqual(pack['total_bytes'], sum(f['size'] for f in pack['files']))
            self.assertEqual(len({f['path'] for f in pack['files']}), pack['file_count'])
            for row in pack['files']:
                self.assertGreater(row['size'], 0)
                self.assertEqual(len(row['git_blob_sha1']), 40)
            if pack['recommended_file']:
                self.assertEqual(len(select_files(pack)), 1)
            self.assertEqual(len(select_files(pack, all_files=True)), pack['file_count'])
        self.assertEqual(sum(len(select_files(pack,support_only=True)) for pack in packs), 43)
        self.assertEqual(len(summaries()), 3)

    def test_bundled_support_files_are_complete_and_match_pinned_sources(self):
        root = Path(__file__).resolve().parents[1] / 'vendor' / 'model-packs'
        for pack in manifests():
            for row in select_files(pack, support_only=True):
                path = root / pack['id'] / row['path']
                self.assertTrue(path.is_file(), str(path))
                # Only local Git filter settings are intentionally adapted.
                if row['path'] != '.gitattributes':
                    self.assertTrue(verify_file(path,row), str(path))

    def test_destinations_reject_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['../secret', '/absolute', 'C:/secret', 'folder\\secret']:
                with self.assertRaises(ValueError): destination(root,name)
            self.assertEqual(destination(root,'BF16/one.gguf'), root/'BF16'/'one.gguf')

    def test_integrity_download_failure_never_replaces_existing_file(self):
        data = b'fixture weights'
        spec = {'path':'weights.gguf','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        pack = {'source_repo':'owner/model','revision':'a'*40}
        response = Mock(); response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [data]
        with tempfile.TemporaryDirectory() as folder, patch('agent.packs.requests.get',return_value=response) as get:
            root = Path(folder)
            self.assertTrue(download_file(pack,spec,root))
            self.assertTrue(verify_file(root/'weights.gguf',spec))
            self.assertFalse(download_file(pack,spec,root))
            self.assertEqual(get.call_count,1)
            self.assertNotIn('headers',get.call_args.kwargs)
            (root/'weights.gguf').write_bytes(b'old')
            response.iter_content.return_value=[b'bad']
            with self.assertRaises(ValueError): download_file(pack,spec,root)
            self.assertEqual((root/'weights.gguf').read_bytes(),b'old')
            self.assertEqual(list(root.glob('.zenith-download-*')),[])

    def test_unrecognized_files_cannot_be_downloaded(self):
        with self.assertRaises(ValueError):select_files(manifests()[0],filename='secret.env')

    def test_local_server_contract_has_no_api_key_and_preserves_roles(self):
        settings=Settings(provider='localserver',context_tokens=8192,max_new_tokens=100)
        messages=[{'role':'system','content':'You are Zenith'},{'role':'user','content':'Hello'}]
        with patch('agent.providers.requests.post') as post:
            post.return_value.json.return_value={'choices':[{'message':{'content':'Welcome back'}}]}
            answer,used=LocalServerProvider(settings).generate(messages)
        self.assertEqual(answer,'Welcome back');self.assertEqual(used,messages)
        self.assertEqual(post.call_args.args[0],'http://127.0.0.1:8080/v1/chat/completions')
        self.assertNotIn('headers',post.call_args.kwargs)
        self.assertEqual(post.call_args.kwargs['json']['model'],'zenith')
        with self.assertRaises(ValueError): Settings(provider='localserver',local_server_url='https://external.example/v1')
        with self.assertRaises(ValueError): Settings(provider='localserver',local_server_url='http://name:password@localhost:8080/v1')
