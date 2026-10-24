"""Same-lineage weight averaging preserves originals and never reports new training."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from agent.checkpoints import inventory


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('safetensors'),'Local tensor dependencies')
class StabilizeTests(unittest.TestCase):
    def test_equal_weight_values_ancestor_binding_and_source_immutability(self):
        import torch
        from safetensors.torch import save_file,load_file
        from agent.stabilize import stabilize
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def checkpoint(name,value,parent=None):
                path=root/name;path.mkdir()
                config={'peft_type':'LORA','task_type':'CAUSAL_LM','base_model_name_or_path':'fixture/existing','target_modules':['q_proj','v_proj']}
                if parent:config['target_modules'].reverse()
                (path/'adapter_config.json').write_text(json.dumps(config));(path/'tokenizer.json').write_text('{}')
                save_file({'layer.lora_A.weight':torch.full((1,2),float(value)),'layer.lora_B.weight':torch.full((2,1),float(value))},str(path/'adapter_model.safetensors'))
                report={'base_model':'fixture/existing','base_revision':'a'*40,'tokenizer_sha256':'b'*64,
                    'train_examples':1,'training':{'train_loss':1.0,'train_runtime':1.0,'optimizer_steps':1}}
                if parent:report.update(parent=str(parent),parent_files=inventory(parent))
                (path/'training_report.json').write_text(json.dumps(report));return path
            previous=checkpoint('previous',1);latest=checkpoint('latest',3,previous);unrelated=checkpoint('unrelated',7)
            before={str(p):inventory(p) for p in [previous,latest]}
            report=stabilize(latest,[previous],root/'mean')
            for tensor in load_file(str(root/'mean/adapter_model.safetensors')).values():self.assertTrue(torch.equal(tensor,torch.full_like(tensor,2)))
            self.assertEqual(report['transformation']['optimizer_steps'],0)
            self.assertEqual(report['transformation']['training_tokens'],0)
            self.assertFalse(report['promoted'])
            for p in [previous,latest]:self.assertEqual(inventory(p),before[str(p)])
            with self.assertRaises(ValueError):stabilize(latest,[unrelated],root/'bad')
            with self.assertRaises(ValueError):stabilize(latest,[previous],latest/'nested')


if __name__=='__main__':unittest.main()
