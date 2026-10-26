"""Dataset export and assistant-only chat loss formatting."""
import hashlib
import json
import random
from pathlib import Path


def split_examples(examples, eval_fraction=0.2, seed=42):
    """Deduplicate examples and keep repeated user prompts in the same split."""
    if not 0 < eval_fraction < 1:
        raise ValueError('eval_fraction must be between 0 and 1')
    # Union conversations and repeated prompts before deduplication. Otherwise a
    # held-out answer could occur in a later training turn's conversation context.
    examples = list(examples)
    parents = list(range(len(examples)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    def union(left, right):
        parents[find(right)] = find(left)
    owners = {}
    for index, row in enumerate(examples):
        messages = row['messages']
        prompt = row.get('prompt') or next(m['content'] for m in reversed(messages) if m['role'] == 'user')
        keys = [('prompt', ' '.join(prompt.casefold().split()))]
        if row.get('conversation_id'):
            keys.append(('conversation', row['conversation_id']))
        for key in keys:
            if key in owners:
                union(index, owners[key])
            else:
                owners[key] = index
    groups, seen = {}, set()
    for index, row in enumerate(examples):
        fingerprint = json.dumps(row['messages'], sort_keys=True, ensure_ascii=False)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        groups.setdefault(find(index), []).append(row)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    count = min(len(keys) - 1, max(1, round(len(keys) * eval_fraction))) if len(keys) >= 2 else 0
    held_out = set(keys[:count])
    train, evaluation = [], []
    for key in keys:
        (evaluation if key in held_out else train).extend(groups[key])
    return train, evaluation


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    temporary.replace(path)


def load_examples(path):
    result = []
    with Path(path).open(encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row.get('messages')
            if not isinstance(messages, list) or len(messages) < 2:
                raise ValueError(f'{path}:{line_number}: expected chat messages')
            for message in messages:
                if message.get('role') not in {'system', 'user', 'assistant'} or not isinstance(message.get('content'), str) or not message['content'].strip():
                    raise ValueError(f'{path}:{line_number}: invalid message')
            if messages[-1]['role'] != 'assistant' or messages[-2]['role'] != 'user':
                raise ValueError(f'{path}:{line_number}: expected a final user/assistant pair')
            result.append(row)
    return result


def prepare_chat_example(tokenizer, messages, max_length):
    """Train on the final assistant response; ignore prompt and padding loss."""
    full = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False, add_generation_prompt=False)
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=True, return_dict=False, add_generation_prompt=True)
    if full[:len(prefix)] != prefix:
        raise ValueError('This model chat template does not have a stable assistant prefix')
    if len(full) > max_length or len(full) <= len(prefix):
        return None
    return {'input_ids': full, 'attention_mask': [1] * len(full),
            'labels': [-100] * len(prefix) + full[len(prefix):]}


class ChatCollator:
    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, rows):
        import torch
        length = max(len(row['input_ids']) for row in rows)
        result = {'input_ids': [], 'attention_mask': [], 'labels': []}
        for row in rows:
            padding = length - len(row['input_ids'])
            result['input_ids'].append(row['input_ids'] + [self.pad_token_id] * padding)
            result['attention_mask'].append(row['attention_mask'] + [0] * padding)
            result['labels'].append(row['labels'] + [-100] * padding)
        return {name: torch.tensor(values, dtype=torch.long) for name, values in result.items()}


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
