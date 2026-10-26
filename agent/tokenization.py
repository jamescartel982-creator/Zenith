"""Load saved tokenizer definitions without rebuilding a frozen Qwen2 backend."""
import json
from pathlib import Path


def legacy_special_token_options(configuration):
    additional = configuration.get('additional_special_tokens')
    if isinstance(additional, list) and additional and not configuration.get('extra_special_tokens'):
        return {'extra_special_tokens': additional}
    return {}


def load_preserved_tokenizer(model, **kwargs):
    from transformers import AutoTokenizer, PreTrainedTokenizerFast, __version__
    kwargs['trust_remote_code'] = False
    tokenizer = AutoTokenizer.from_pretrained(model, **kwargs)
    if int(__version__.split('.')[0]) >= 5 and type(tokenizer).__name__ == 'Qwen2Tokenizer':
        # Transformers 5's Qwen2 class rebuilds its ByteLevel components with
        # new defaults. The generic public fast-tokenizer loader instead uses
        # the saved tokenizer.json backend, including its exact added tokens.
        configuration = Path(model) / 'tokenizer_config.json'
        if not configuration.is_file():
            from huggingface_hub import hf_hub_download
            configuration = Path(hf_hub_download(str(model), 'tokenizer_config.json',
                revision=kwargs.get('revision'), local_files_only=kwargs.get('local_files_only', False),
                token=kwargs.get('token')))
        # Older saved adapters include extra_special_tokens={} alongside the
        # original additional_special_tokens list. The new API gives the empty
        # dictionary precedence unless the legacy list is passed explicitly.
        options = legacy_special_token_options(json.loads(configuration.read_text(encoding='utf-8')))
        tokenizer = PreTrainedTokenizerFast.from_pretrained(model, **{**kwargs, **options})
    return tokenizer
