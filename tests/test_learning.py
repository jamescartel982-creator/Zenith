import importlib.util
import tempfile
import unittest
from pathlib import Path
from agent.learning import split_examples, prepare_chat_example, ChatCollator, write_jsonl, load_examples


class TemplateFixture:
    """A template whose prompt and EOS token boundaries are explicit."""
    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False,return_dict=False):
        tokens = []
        for message in messages:
            tokens += [1 if message['role'] == 'user' else 2] + list(message['content'].encode()) + [0]
        if add_generation_prompt:
            tokens += [2]
        return tokens


class LearningTests(unittest.TestCase):
    def test_prompt_and_context_are_ignored_in_loss(self):
        tokenizer = TemplateFixture()
        messages = [{'role': 'user', 'content': 'Hello'}, {'role': 'assistant', 'content': 'Hi'}]
        row = prepare_chat_example(tokenizer, messages, 100)
        prefix = tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True)
        self.assertTrue(all(value == -100 for value in row['labels'][:len(prefix)]))
        self.assertEqual(row['labels'][len(prefix):], list(b'Hi') + [0])
        self.assertIsNone(prepare_chat_example(tokenizer, messages, 3))

    def test_deduplication_and_repeated_prompts_cannot_cross_split(self):
        def example(prompt, answer):
            return {'messages': [{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}]}
        rows = [example('same question', 'a'), example('SAME  QUESTION', 'b')] + [example(f'prompt {i}', 'answer') for i in range(8)]
        train, evaluation = split_examples(rows + rows)
        self.assertEqual(len(train) + len(evaluation), len(rows))
        normalize = lambda row: ' '.join(row['messages'][0]['content'].casefold().split())
        self.assertFalse({normalize(row) for row in train} & {normalize(row) for row in evaluation})
        self.assertEqual((train, evaluation), split_examples(rows + rows))

    def test_conversation_context_cannot_leak_between_splits(self):
        def example(session, prompt, answer):
            return {'conversation_id': session, 'messages': [
                {'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}]}
        rows = [example('a', 'first', 'one'), example('a', 'second', 'two'),
                example('b', 'third', 'three'), example('b', 'first', 'one'),
                example('c', 'independent', 'four')]
        train, evaluation = split_examples(rows)
        self.assertTrue(train and evaluation)
        train_sessions = {row['conversation_id'] for row in train}
        eval_sessions = {row['conversation_id'] for row in evaluation}
        self.assertFalse(train_sessions & eval_sessions)
        # Shared prompts connect a and b even when one record is deduplicated.
        self.assertTrue({'a', 'b'}.issubset(train_sessions) or {'a', 'b'}.issubset(eval_sessions))

    def test_file_roundtrip_and_invalid_training_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dataset.jsonl'
            rows = [{'messages': [{'role': 'user', 'content': 'Hello'}, {'role': 'assistant', 'content': 'Hi'}]}]
            write_jsonl(path, rows)
            self.assertEqual(load_examples(path), rows)
            write_jsonl(path, [{'text': 'wrong format'}])
            with self.assertRaises(ValueError):
                load_examples(path)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional torch not installed')
    def test_eos_targets_are_not_confused_with_padding(self):
        collator = ChatCollator(pad_token_id=0)
        rows = [{'input_ids': [1, 3, 0], 'labels': [-100, 3, 0], 'attention_mask': [1, 1, 1]},
                {'input_ids': [1, 0], 'labels': [-100, 0], 'attention_mask': [1, 1]}]
        batch = collator(rows)
        self.assertEqual(batch['labels'].tolist(), [[-100, 3, 0], [-100, 0, -100]])
        self.assertEqual(batch['attention_mask'].tolist(), [[1, 1, 1], [1, 1, 0]])
