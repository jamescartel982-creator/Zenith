"""No fresh foundation initialization, replay isolation, and evaluation contracts."""
import json
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.checkpoints import parent_metadata
from agent.continual import prepare_record,sequence_logprob
from agent.expansion_eval import score,compare,rescore_report
from scripts.prepare_expansion_curriculum import build
from agent.learning import load_examples
from agent.curriculum import audit_directory,assert_disjoint,row_keys

ROOT=Path(__file__).resolve().parents[1]


class Tokenizer:
    eos_token_id=9
    def encode(self,text,add_special_tokens=False):return [1,2,3]
    def apply_chat_template(self,messages,tokenize=True,add_generation_prompt=False):
        return [1,2] if add_generation_prompt else [1,2,3,9]


class ContinuationTests(unittest.TestCase):
    def test_absent_or_untrained_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):parent_metadata(folder)
            for name in ['adapter_config.json','tokenizer.json','training_report.json']:
                (Path(folder)/name).write_text('{}')
            (Path(folder)/'adapter_model.safetensors').write_bytes(b'not a checkpoint')
            with self.assertRaises(ValueError):parent_metadata(folder)

    def test_replay_stays_only_in_training_and_all_partitions_are_disjoint(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'dataset'
            manifest=build(output,ROOT/'docs/benchmarks/v0.6/frozen-pilot-dataset/train.jsonl')
            audit_directory(output)
            for path in output.glob('*.jsonl'):
                self.assertNotIn(b'\r\n',path.read_bytes(),str(path))
            rows={name:load_examples(output/manifest['files'][name]['path']) for name in ['train','validation','test']}
            assert_disjoint(rows)
            self.assertTrue(any(row.get('retention_replay') for row in rows['train']))
            self.assertFalse(any(row.get('retention_replay') for name in ['validation','test'] for row in rows[name]))
            original=load_examples(ROOT/'docs/benchmarks/v0.6/frozen-pilot-dataset/train.jsonl')
            original_keys=set().union(*(row_keys(row) for row in original))
            self.assertFalse(any(row_keys(row)&original_keys for name in ['validation','test'] for row in rows[name]))
            with self.assertRaises(ValueError):build(output,ROOT/'docs/benchmarks/v0.6/frozen-pilot-dataset/train.jsonl')

    def test_sft_cpt_and_dpo_have_explicit_targets_and_mask_prompts(self):
        row={'messages':[{'role':'user','content':'Question'},{'role':'assistant','content':'Correct'}],
             'text':'Domain corpus','chosen':'Correct','rejected':'Incorrect','preference_validated':True}
        sft=prepare_record(Tokenizer(),row,32,'sft')
        self.assertEqual(sft['labels'],[-100,-100,3,9])
        cpt=prepare_record(Tokenizer(),row,32,'cpt')
        self.assertEqual(cpt['input_ids'],cpt['labels'])
        dpo=prepare_record(Tokenizer(),row,32,'dpo')
        self.assertEqual(set(dpo),{'chosen','rejected'})
        with self.assertRaises(ValueError):prepare_record(Tokenizer(),{'messages':row['messages']},32,'dpo')

    def test_diagnostic_json_and_code_scorers_never_execute_outputs(self):
        self.assertTrue(score('{"tool":"calculator","arguments":{"text":"9+8"}}','tool-json',['calculator','9+8']))
        self.assertFalse(score('{"tool":"shell","arguments":{"text":"9+8"}}','tool-json',['calculator','9+8']))
        self.assertTrue(score('def add(a,b):\n    return a+b','python-add',[]))
        self.assertFalse(score('import os\ndef add(a,b):\n    return a+b','python-add',[]))
        self.assertFalse(score('def add(a,b):\n    return a-b','python-add',[]))

    def test_incomplete_algebra_and_markdown_wrapped_json_are_not_success(self):
        self.assertFalse(score('To solve 5x - 7 = 18, first add 7.','algebra-x',['5']))
        self.assertFalse(score('x = 24','algebra-x',['5']))
        self.assertTrue(score('x = 5','algebra-x',['5']))
        self.assertFalse(score('```json\n{"ready":true}\n```','ready-json',[]))

    def test_regressions_fail_promotion_even_when_overall_score_rises(self):
        folder=ROOT/'docs/benchmarks/continuation-v1'
        parent=rescore_report(json.loads((folder/'parent-benchmark.json').read_text()))
        candidate=rescore_report(json.loads((folder/'candidate-benchmark.json').read_text()))
        production=rescore_report(json.loads((folder/'production-benchmark.json').read_text()))
        self.assertGreater(candidate['accuracy'],parent['accuracy'])
        result=compare(parent,candidate,production)
        self.assertFalse(result['numeric_gate_passed'])
        self.assertFalse(result['deployment_approved'])
        self.assertIn('instruction-following',result['regressed_slices'])
        self.assertIn('retrieval-grounding',result['regressed_slices'])

    def test_sentence_punctuation_does_not_hide_a_correct_answer(self):
        self.assertTrue(score('Add seven, then divide: x = 5.','algebra-x',['5']))
        for wrong in ['x = 50.','x = 5.2','x = 5/2','x = 5e3']:
            self.assertFalse(score(wrong,'algebra-x',['5']))
        self.assertTrue(score('No. Stop until the target is authorized.','contains-any',['not execute','do not','stop','must not','no,']))
        self.assertFalse(score('Nobody should decide.','contains-any',['no,']))

    def test_promotion_rejects_incomplete_forged_and_mismatched_reports(self):
        original=rescore_report(json.loads((ROOT/'docs/benchmarks/continuation-v1/candidate-benchmark.json').read_text()))
        for mutation in ['budget','missing-case','fake-score','missing-slice','old-scorer','system-policy','prompt-hash']:
            changed=copy.deepcopy(original)
            if mutation=='budget':changed['max_new_tokens']=128
            elif mutation=='missing-case':changed['results'].pop()
            elif mutation=='fake-score':changed['results'][2]['passed']=True
            elif mutation=='missing-slice':changed['slices'].pop('retrieval-grounding')
            elif mutation=='system-policy':changed['system_prompt']='Different application policy'
            elif mutation=='prompt-hash':changed['system_prompt_sha256']='0'*64
            else:changed['scoring_version']=2
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):compare(original,changed,original)

    def test_case_regression_cannot_hide_inside_unchanged_slice_average(self):
        original=rescore_report(json.loads((ROOT/'docs/benchmarks/continuation-v1/parent-benchmark.json').read_text()))
        changed=copy.deepcopy(original)
        for row in changed['results']:
            if row['id']=='math-1':row['answer']='x = 5.'
            if row['id']=='math-2':row['answer']='I do not know.'
        changed=rescore_report(changed)
        self.assertEqual(changed['slices']['mathematical-reasoning'],original['slices']['mathematical-reasoning'])
        result=compare(original,changed,original)
        self.assertFalse(result['numeric_gate_passed'])
        self.assertEqual(result['regressed_slices'],[])
        self.assertIn('math-2',result['regressed_cases'])

    def test_rescoring_preserves_original_report_and_raw_answers(self):
        original=json.loads((ROOT/'docs/benchmarks/continuation-v1/candidate-benchmark.json').read_text())
        before=copy.deepcopy(original)
        result=rescore_report(original)
        self.assertEqual(original,before)
        self.assertEqual([r['answer'] for r in result['results']],[r['answer'] for r in original['results']])
        self.assertEqual(result['scoring_version'],3)
