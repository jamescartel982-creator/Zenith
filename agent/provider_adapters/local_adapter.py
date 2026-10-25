"""Bridge existing Zenith runtimes without changing their weights or tokenizer."""
from dataclasses import replace
from urllib.parse import urlsplit
from .common import AdapterError, DeadlineCancel, final_completion, request_json, text_messages
from ..model_capabilities import ModelCapabilities, ModelRecord


def loopback(url):
    parsed = urlsplit(url)
    return (parsed.scheme in {'http', 'https'} and parsed.hostname in {'localhost', '127.0.0.1', '::1'}
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment)


class LocalAdapter:
    def __init__(self, name, settings):
        self.name, self.settings, self.providers = name, settings, {}
        self.bindings = {}

    def bind(self, record, settings):
        if settings.provider not in {'huggingface', 'ollama', 'localserver', 'tiny'}:
            raise ValueError('Local bindings must use an existing single-model provider')
        if settings.provider in {'ollama', 'localserver'}:
            url = settings.ollama_url if settings.provider == 'ollama' else settings.local_server_url
            if not loopback(url):
                raise ValueError('Local orchestration endpoints must be loopback URLs')
        self.bindings[record.key] = settings

    def discover(self, context):
        if self.name not in {'ollama', 'localserver'}:
            return []
        url = self.settings.ollama_url if self.name == 'ollama' else self.settings.local_server_url
        if not loopback(url):
            raise ValueError('Discovery requires a loopback server')
        data = request_json('GET', url + ('/api/tags' if self.name == 'ollama' else '/models'), context)
        rows = data.get('models' if self.name == 'ollama' else 'data')
        if not isinstance(rows, list):
            raise AdapterError('invalid_model_list')
        result = []
        for row in rows[:10000]:
            identifier = row.get('name' if self.name == 'ollama' else 'id') if isinstance(row, dict) else None
            if not isinstance(identifier, str):
                raise AdapterError('invalid_model_list')
            result.append(ModelRecord(self.name, identifier, 'listed', local=True,
                capabilities=ModelCapabilities(), provenance='Configured loopback model listing',
                access='Server-visible; text inference compatibility still required'))
        return result

    def generate(self, record, messages, context):
        context.check()
        used = text_messages(messages)
        settings = self.bindings.get(record.key)
        if settings is None:
            raise AdapterError('local_model_not_bound')
        from ..providers import make_provider
        if record.key not in self.providers:
            self.providers[record.key] = make_provider(settings)
        provider = self.providers[record.key]
        old = provider.settings
        provider.settings = replace(old, max_new_tokens=min(old.max_new_tokens, context.max_output_tokens), offline=True)
        try:
            if callable(getattr(provider, 'stream', None)):
                signal = DeadlineCancel(context)
                iterator = provider.stream(used, signal)
                chunks, size = [], 0
                try:
                    for chunk, used in iterator:
                        context.check()
                        size += len(chunk)
                        if size > 150000:
                            raise AdapterError('response_too_large')
                        chunks.append(chunk)
                finally:
                    signal.set()
                    iterator.close()
                text = ''.join(chunks)
            else:
                text, used = provider.generate(used)
            context.check()
            return final_completion(text, used, getattr(provider, 'last_usage', None))
        finally:
            provider.settings = old
