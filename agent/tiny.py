"""Zenith Tiny: an original byte-level decoder-only transformer.

Educational from-scratch model; random initialization is not a capable assistant.
Uses PyTorch attention kernels, learned positions, pre-norm blocks, and tied weights.
"""
from dataclasses import asdict, dataclass
import torch
from torch import nn
from torch.nn import functional as F

EOS = 256
VOCAB_SIZE = 257


def encode(text):
    return list(text.encode('utf-8'))


def decode(ids):
    return bytes(i for i in ids if 0 <= i < 256).decode('utf-8', errors='replace')


@dataclass
class TinyConfig:
    context_length: int = 512
    width: int = 128
    heads: int = 4
    layers: int = 4
    dropout: float = 0.1

    def __post_init__(self):
        if self.width < 8 or self.heads < 1 or self.width % self.heads or self.layers < 1 or self.context_length < 8 or not 0 <= self.dropout < 1:
            raise ValueError('Invalid tiny transformer configuration')


class Block(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.heads = config.heads
        self.norm1 = nn.LayerNorm(config.width)
        self.norm2 = nn.LayerNorm(config.width)
        self.qkv = nn.Linear(config.width, 3 * config.width, bias=False)
        self.projection = nn.Linear(config.width, config.width, bias=False)
        self.mlp = nn.Sequential(nn.Linear(config.width, 4 * config.width), nn.GELU(), nn.Linear(4 * config.width, config.width), nn.Dropout(config.dropout))
        self.dropout = config.dropout

    def forward(self, x):
        batch, length, width = x.shape
        q, k, v = self.qkv(self.norm1(x)).chunk(3, dim=-1)
        q, k, v = [item.view(batch, length, self.heads, width // self.heads).transpose(1, 2) for item in (q, k, v)]
        attention = F.scaled_dot_product_attention(q, k, v, is_causal=True, dropout_p=self.dropout if self.training else 0.0)
        x = x + self.projection(attention.transpose(1, 2).contiguous().view(batch, length, width))
        return x + self.mlp(self.norm2(x))


class TinyLM(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.tokens = nn.Embedding(VOCAB_SIZE, config.width)
        self.positions = nn.Embedding(config.context_length, config.width)
        self.blocks = nn.Sequential(*(Block(config) for _ in range(config.layers)))
        self.norm = nn.LayerNorm(config.width)
        self.head = nn.Linear(config.width, VOCAB_SIZE, bias=False)
        self.head.weight = self.tokens.weight
        self.apply(self._init)

    @staticmethod
    def _init(module):
        if isinstance(module, (nn.Embedding, nn.Linear)):
            nn.init.normal_(module.weight, mean=0, std=0.02)
            if getattr(module, 'bias', None) is not None:
                nn.init.zeros_(module.bias)

    def forward(self, input_ids, labels=None):
        if input_ids.shape[1] > self.config.context_length:
            raise ValueError('Input exceeds tiny context window')
        positions = torch.arange(input_ids.shape[1], device=input_ids.device)
        x = self.tokens(input_ids) + self.positions(positions)
        logits = self.head(self.norm(self.blocks(x)))
        # Training script supplies labels already shifted one byte to the right.
        loss = None if labels is None else F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), labels.reshape(-1))
        return logits, loss

    @torch.inference_mode()
    def generate(self, ids, max_new_tokens=128, temperature=0.7):
        self.eval()
        for _ in range(max_new_tokens):
            logits, _ = self(ids[:, -self.config.context_length:])
            logits = logits[:, -1, :]
            next_id = logits.argmax(-1, keepdim=True) if temperature == 0 else torch.multinomial(F.softmax(logits / temperature, dim=-1), num_samples=1)
            ids = torch.cat((ids, next_id), dim=1)
            if torch.all(next_id == EOS):
                break
        return ids


def save_checkpoint(model, path):
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'format_version': 1, 'config': asdict(model.config), 'state_dict': model.state_dict()}, path)


def load_checkpoint(path, device='cpu'):
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if checkpoint.get('format_version') != 1:
        raise ValueError('Unsupported Zenith Tiny checkpoint')
    model = TinyLM(TinyConfig(**checkpoint['config'])).to(device)
    model.load_state_dict(checkpoint['state_dict'])
    return model.eval()
