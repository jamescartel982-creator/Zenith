"""Load saved tokenizer definitions without rebuilding a frozen Qwen2 backend."""


def load_preserved_tokenizer(model, **kwargs):
    from transformers import AutoTokenizer, PreTrainedTokenizerFast, __version__
    kwargs['trust_remote_code'] = False
    tokenizer = AutoTokenizer.from_pretrained(model, **kwargs)
    if int(__version__.split('.')[0]) >= 5 and type(tokenizer).__name__ == 'Qwen2Tokenizer':
        # Transformers 5's Qwen2 class rebuilds its ByteLevel components with
        # new defaults. The generic public fast-tokenizer loader instead uses
        # the saved tokenizer.json backend, including its exact added tokens.
        tokenizer = PreTrainedTokenizerFast.from_pretrained(model, **kwargs)
    return tokenizer
