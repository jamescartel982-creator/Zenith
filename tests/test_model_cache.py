"""Partial, weight-only Hub snapshots remain valid with strict offline checking."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.models import WEIGHT_PATTERNS, cache_status, download


class WeightSnapshotTests(unittest.TestCase):
    def test_download_and_validation_use_the_same_snapshot_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('config.json', 'tokenizer_config.json', 'model.safetensors', 'tokenizer.json'):
                (root / name).write_text('{}')
            calls = []

            def snapshot(repo_id, **kwargs):
                # New Hub refuses a partial snapshot when a caller asks for
                # all repository files (e.g. excluded .gitattributes).
                if kwargs.get('allow_patterns') != WEIGHT_PATTERNS:
                    raise RuntimeError('Requested snapshot is incomplete')
                calls.append(kwargs)
                return str(root)

            spec = {'provider': 'huggingface', 'model': 'fixture/not-executed', 'revision': 'pinned'}
            with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=snapshot)}):
                self.assertTrue(download(spec, offline=True)['cached'])
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call['local_files_only'] for call in calls))

    def test_matching_filter_does_not_accept_missing_weight_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('config.json', 'tokenizer_config.json', 'tokenizer.json'):
                (root / name).write_text('{}')
            sdk = SimpleNamespace(snapshot_download=lambda *a, **k: str(root))
            with patch.dict(sys.modules, {'huggingface_hub': sdk}):
                state = cache_status({'provider': 'huggingface', 'model': 'fixture/not-executed', 'revision': 'pinned'})
            self.assertFalse(state['cached'])
            self.assertIn('model.safetensors', state['reason'])
