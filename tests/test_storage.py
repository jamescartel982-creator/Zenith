import tempfile
import unittest
from agent.storage import Store


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(self.directory.name)
        self.messages = [{'role': 'system', 'content': 'System'}, {'role': 'user', 'content': 'Hello'}]
        self.turn = self.store.add('a', 'Hello', 'World', self.messages, 'test-model')

    def test_session_isolation_and_persistence(self):
        self.assertEqual(self.store.history('b'), [])
        self.assertEqual(Store(self.directory.name).history('a')[0]['response'], 'World')
        self.assertFalse(self.store.review('b', self.turn, 'good', True))
        self.assertEqual(self.store.approved_examples(), [])

    def test_only_explicit_latest_approval_is_exported(self):
        self.store.review('a', self.turn, 'good')
        self.assertEqual(self.store.approved_examples(), [])
        self.store.review('a', self.turn, 'good', True)
        self.store.review('a', self.turn, 'good', True)
        self.assertEqual(len(self.store.approved_examples()), 1)
        self.store.review('a', self.turn, 'bad')
        self.assertEqual(self.store.approved_examples(), [])

    def test_corrected_bad_answer_preserves_context(self):
        with self.assertRaises(ValueError):
            self.store.review('a', self.turn, 'bad', True)
        self.store.review('a', self.turn, 'bad', True, 'Better answer')
        row = self.store.approved_examples()[0]
        self.assertEqual(row['messages'][:-1], self.messages)
        self.assertEqual(row['messages'][-1]['content'], 'Better answer')
        self.assertEqual(self.store.history('a')[0]['response'], 'World')

    def test_delete_removes_training_approval(self):
        self.store.review('a', self.turn, 'good', True)
        self.store.delete_session('b')
        self.assertEqual(len(self.store.history('a')), 1)
        self.store.delete_session('a')
        self.assertEqual(self.store.history('a'), [])
        self.assertEqual(self.store.approved_examples(), [])
