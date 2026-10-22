import importlib.util
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Optional torch not installed')
class TinyTests(unittest.TestCase):
    def test_attention_is_causal(self):
        import torch
        from agent.tiny import TinyLM, TinyConfig
        torch.manual_seed(42)
        model = TinyLM(TinyConfig(context_length=16, width=16, layers=1, heads=2, dropout=0)).eval()
        a = torch.tensor([[1, 2, 3, 4]])
        b = torch.tensor([[1, 2, 9, 8]])
        with torch.no_grad():
            logits_a, _ = model(a)
            logits_b, _ = model(b)
        self.assertTrue(torch.allclose(logits_a[:, :2], logits_b[:, :2], atol=1e-6))
        self.assertFalse(torch.allclose(logits_a[:, 2:], logits_b[:, 2:]))

    def test_backpropagation_checkpoint_and_generation(self):
        import torch
        from agent.tiny import TinyLM, TinyConfig, save_checkpoint, load_checkpoint, encode, decode
        model = TinyLM(TinyConfig(context_length=16, width=16, layers=1, heads=2, dropout=0))
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        ids = torch.tensor([encode('Hello')])
        previous = model.tokens.weight.detach().clone()
        _, loss = model(ids[:, :-1], ids[:, 1:])
        loss.backward(); optimizer.step()
        self.assertTrue(torch.isfinite(loss))
        self.assertFalse(torch.equal(previous, model.tokens.weight))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.pt'
            save_checkpoint(model, path)
            loaded = load_checkpoint(path)
            model.eval()
            self.assertTrue(torch.equal(model(ids)[0], loaded(ids)[0]))
            generated = loaded.generate(ids, max_new_tokens=2, temperature=0)
            self.assertGreater(generated.shape[1], ids.shape[1])
        self.assertEqual(decode(encode('Unicode: café 🙂')), 'Unicode: café 🙂')
