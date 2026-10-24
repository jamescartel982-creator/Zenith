"""Reconstruction preserves exact checkpoint bytes and rejects changed artifacts."""
import json
from pathlib import Path
import tempfile
import unittest
from agent.checkpoints import inventory
from agent.research import materialize


class ResearchCheckpointTests(unittest.TestCase):
    def test_exact_reconstruction_and_modified_parts_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);bundle=root/'bundle';source=bundle/'checkpoint';source.mkdir(parents=True)
            (source/'tokenizer.json').write_bytes(b'{"vocab":"unchanged"}\n')
            complete=root/'original';complete.mkdir();(complete/'tokenizer.json').write_bytes((source/'tokenizer.json').read_bytes())
            (complete/'adapter_model.safetensors').write_bytes(b'actual-test-bytes')
            (bundle/'part1').write_bytes(b'actual-');(bundle/'part2').write_bytes(b'test-bytes')
            manifest={'schema_version':1,'approved_for_local_activation':False,'checkpoint':'checkpoint','weight_file':'adapter_model.safetensors','weight_parts':['part1','part2'],'checkpoint_files':inventory(complete),'files':inventory(bundle)}
            (bundle/'research.json').write_text(json.dumps(manifest))
            before=inventory(bundle)
            with self.assertRaises(ValueError):materialize(bundle,bundle/'output')
            output=root/'reconstructed';materialize(bundle,output)
            self.assertEqual(inventory(output),inventory(complete));self.assertEqual(inventory(bundle),before)
            with self.assertRaises(ValueError):materialize(bundle,output)
            (bundle/'part2').write_bytes(b'modified')
            with self.assertRaises(ValueError):materialize(bundle,root/'bad')
            self.assertFalse((root/'bad').exists())
