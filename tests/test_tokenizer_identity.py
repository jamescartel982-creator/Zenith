"""Fingerprint aliases must preserve lineage while detecting real changes."""
from types import SimpleNamespace
import unittest

from agent.checkpoints import tokenizer_signature


class TokenizerIdentityTests(unittest.TestCase):
    def fixture(self, *, modern=False, extra=None, backend='{"model":{"vocab":{"a":0}}}'):
        extra = ['<start>', '<end>'] if extra is None else extra
        values = {'backend_tokenizer': SimpleNamespace(to_str=lambda: backend),
                  'chat_template': 'unchanged template', 'special_tokens_map': {'eos_token': '<end>'},
                  'bos_token_id': None, 'eos_token_id': 2, 'pad_token_id': 0}
        if modern:
            values['extra_special_tokens'] = extra
        else:
            values['special_tokens_map']['additional_special_tokens'] = extra
        return SimpleNamespace(**values)

    def test_public_attribute_rename_preserves_the_original_fingerprint(self):
        self.assertEqual(tokenizer_signature(self.fixture()), tokenizer_signature(self.fixture(modern=True)))

    def test_changed_tokens_backend_or_template_still_change_the_fingerprint(self):
        original = tokenizer_signature(self.fixture())
        self.assertNotEqual(original, tokenizer_signature(self.fixture(modern=True, extra=['different'])))
        self.assertNotEqual(original, tokenizer_signature(self.fixture(backend='{"model":{"vocab":{"a":1}}}')))
        changed = self.fixture()
        changed.chat_template = 'different template'
        self.assertNotEqual(original, tokenizer_signature(changed))
