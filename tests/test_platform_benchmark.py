"""Benchmark checkpoint selection cannot become production activation."""
from pathlib import Path
from unittest.mock import patch
import unittest

from agent.config import Settings
from scripts.platform_benchmark import measure


class BenchmarkSelectionTests(unittest.TestCase):
    def test_explicit_bundle_is_verified_twice_and_materialized_only_in_temporary_path(self):
        original = Settings(adapter='', checkpoint_receipt='', provider='huggingface')
        manifest = {'base_model': original.model, 'base_revision': original.revision}
        paths = []
        def materialize(source, output):
            path = Path(output); path.mkdir()
            (path/'adapter_model.safetensors').write_bytes(b'unit selection fixture; not a real model')
            paths.append(path)
        def run(samples, baseline, selected):
            self.assertIs(baseline, original)
            self.assertEqual(selected.model, original.model)
            self.assertEqual(selected.checkpoint_receipt, '')
            self.assertTrue(Path(selected.adapter).is_dir())
            self.assertEqual(baseline.adapter, '')
            return {'samples': samples}
        with patch('agent.config.Settings', return_value=original), patch('agent.research.verify_bundle', return_value=(Path('/fixture'), manifest)) as verify, patch('agent.research.materialize', side_effect=materialize), patch('scripts.platform_benchmark._measure', side_effect=run):
            result = measure(1, Path('/fixture'))
        self.assertEqual(verify.call_count, 2)
        self.assertIn('no profile activation', result['selection'])
        self.assertFalse(paths[0].exists())

    def test_wrong_base_and_missing_adapter_do_not_silently_select_another_model(self):
        original = Settings(adapter='', provider='huggingface')
        with patch('agent.config.Settings', return_value=original):
            with self.assertRaises(ValueError): measure()
            with patch('agent.research.verify_bundle', return_value=(Path('/fixture'), {'base_model': 'a-different-brain'})), patch('agent.research.materialize') as writer:
                with self.assertRaises(ValueError): measure(1, Path('/fixture'))
                writer.assert_not_called()
