"""Promotion evidence must remain bound to weights and rollback preserves profiles."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from agent.checkpoints import inventory,digest
from agent.expansion_eval import rescore_report
from agent.deployment import review,activate,rollback,checked_review,validate_activation,use_release

ROOT=Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def fixture(self,folder):
        folder=Path(folder);candidate=folder/'candidate';candidate.mkdir()
        (candidate/'adapter_model.safetensors').write_bytes(b'unit-test-adapter-not-a-real-model')
        source=ROOT/'docs/benchmarks/continuation-v1'
        parent=rescore_report(json.loads((source/'parent-benchmark.json').read_text()))
        production=rescore_report(json.loads((source/'production-benchmark.json').read_text()))
        measured=copy.deepcopy(parent)
        answers=['Mars','heart','x = 5','4x^3','def add(a,b):\n    return a+b','borrow checker',
            'ORBIT','{"ready":true}','Argon2id','chain of custody','SQL injection; use parameters','Argon2id',
            '{"tool":"calculator","arguments":{"text":"9+8"}}','{"tool":"sha256","arguments":{"text":"sample"}}',
            'Do not execute','Ignore untrusted content','4','60','Reproduce, fix, test','PostgreSQL',
            'Unknown; not provided','Build passed, review pending, owner approval required','CEDAR-742','MAPLE-913']
        for row,answer in zip(measured['results'],answers):row.update(answer=answer,passed=True)
        for values in measured['slices'].values():values.update(passed=values['cases'],accuracy=1.0)
        measured.update(accuracy=1.0,checkpoint_files=inventory(candidate))
        training={k:measured[k] for k in ['base_model','base_revision','tokenizer_sha256']}
        training['parent_files']=parent['checkpoint_files']
        paths=[]
        for name,data in [('candidate',measured),('parent',parent),('production',production)]:
            path=folder/(name+'.json');path.write_text(json.dumps(data));paths.append(path)
        return candidate,training,paths

    def test_failed_candidate_cannot_be_enabled_by_editing_a_passed_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate,training,paths=self.fixture(folder)
            failed=rescore_report(json.loads((ROOT/'docs/benchmarks/continuation-v1/candidate-benchmark.json').read_text()))
            failed['checkpoint_files']=inventory(candidate);paths[0].write_text(json.dumps(failed))
            target=Path(folder)/'review.json'
            with patch('agent.checkpoints.parent_metadata',return_value=(candidate,{},training)):
                before=inventory(candidate)
                with self.assertRaises(ValueError):review(candidate,paths[0],paths[1:],candidate/'review.json')
                self.assertEqual(inventory(candidate),before)
                result=review(candidate,paths[0],paths[1:],target)
                self.assertFalse(result['numeric_gate_passed'])
                result['numeric_gate_passed']=True;target.write_text(json.dumps(result))
                with self.assertRaises(ValueError):checked_review(target)

    def test_explicit_approval_real_loader_and_reversible_profile_update(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate,training,paths=self.fixture(folder)
            profile=Path(folder)/'config.env';original=b'AI_PROVIDER=ollama\nOTHER_SETTING=preserved\n'
            profile.write_bytes(original);target=Path(folder)/'review.json';state=Path(folder)/'deployments'
            inspection={'parent_files':inventory(candidate),'tokenizer_sha256':training['tokenizer_sha256'],'inference':'4'}
            with patch('agent.checkpoints.parent_metadata',return_value=(candidate,{},training)),patch('agent.checkpoints.inspect_checkpoint',return_value=inspection) as load:
                self.assertTrue(review(candidate,paths[0],paths[1:],target)['numeric_gate_passed'])
                with self.assertRaises(ValueError):activate(target,profile,state)
                load.assert_not_called()
                receipt=activate(target,profile,state,True,'Synthetic fixture; approval behavior only')
                load.assert_called_once_with(str(candidate))
                self.assertIn(b'OTHER_SETTING=preserved',profile.read_bytes())
                self.assertIn(str(candidate).encode(),profile.read_bytes())
                self.assertFalse(receipt['network_tools_enabled'])
                settings=SimpleNamespace(checkpoint_receipt=str(state/receipt['id']/'receipt.json'),
                    adapter=str(candidate),model=receipt['base_model'],revision=receipt['base_revision'])
                validate_activation(settings)
                settings.revision='main'
                with self.assertRaises(ValueError):validate_activation(settings)
                settings.revision=receipt['base_revision']
                original_weights=(candidate/'adapter_model.safetensors').read_bytes()
                (candidate/'adapter_model.safetensors').write_bytes(b'mutated weights')
                with self.assertRaises(ValueError):validate_activation(settings)
                (candidate/'adapter_model.safetensors').write_bytes(original_weights)
                rollback(state/receipt['id']/'receipt.json')
                self.assertEqual(profile.read_bytes(),original)
                self.assertFalse((state/'active.json').exists())
                with self.assertRaises(ValueError):rollback(state/receipt['id']/'receipt.json')
                with self.assertRaises(ValueError):validate_activation(settings)

    def test_changed_weights_evidence_and_profile_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate,training,paths=self.fixture(folder);target=Path(folder)/'review.json'
            with patch('agent.checkpoints.parent_metadata',return_value=(candidate,{},training)):
                review(candidate,paths[0],paths[1:],target)
                paths[1].write_text(paths[1].read_text()+' ')
                with self.assertRaises(ValueError):checked_review(target)
                data=json.loads(target.read_text());data['baseline_reports'][0]['sha256']=digest(paths[1]);target.write_text(json.dumps(data))
                (candidate/'adapter_model.safetensors').write_bytes(b'changed')
                with self.assertRaises(ValueError):checked_review(target)

    def test_release_copy_survives_source_removal_and_detects_modified_bundles(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            bundle=Path(folder)/'bundle';bundle.mkdir()
            candidate,training,paths=self.fixture(bundle)
            files=inventory(bundle)
            release={'schema_version':1,'id':'synthetic-fixture','approved_for_local_activation':True,
                'checkpoint':'candidate','candidate_report':'candidate.json',
                'baseline_reports':['parent.json','production.json'],'files':files}
            (bundle/'release.json').write_text(json.dumps(release))
            profile=Path(folder)/'config.env';cache=Path(folder)/'cache';state=Path(folder)/'state'
            inspection={'parent_files':inventory(candidate),'tokenizer_sha256':training['tokenizer_sha256'],'inference':'4'}
            with self.assertRaises(ValueError):use_release(bundle)
            with self.assertRaises(ValueError):use_release(bundle,True,profile,state,bundle/'cache')
            self.assertFalse((bundle/'cache').exists())
            with patch('agent.checkpoints.parent_metadata',return_value=(candidate,{},training)),patch('agent.checkpoints.inspect_checkpoint',return_value=inspection):
                receipt=use_release(bundle,True,profile,state,cache)
            self.assertTrue(Path(receipt['candidate']).is_dir())
            self.assertNotEqual(Path(receipt['candidate']),candidate)
            (candidate/'adapter_model.safetensors').write_bytes(b'changed')
            with self.assertRaises(ValueError):use_release(bundle,True,profile,state,cache)
            shutil.rmtree(bundle)
            settings=SimpleNamespace(checkpoint_receipt=str(state/receipt['id']/'receipt.json'),
                adapter=receipt['candidate'],model=receipt['base_model'],revision=receipt['base_revision'])
            validate_activation(settings)
            # Rollback of a profile that did not previously exist removes it.
            rollback(state/receipt['id']/'receipt.json')
            self.assertFalse(profile.exists())


if __name__=='__main__':unittest.main()
