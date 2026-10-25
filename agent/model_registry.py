"""Unified runtime registry, separate from the existing public reference catalog."""
import argparse
from dataclasses import replace
import json
import os
import time
from .config import Settings
from .model_capabilities import ModelCapabilities, ModelRecord, ProviderAdapter
from .provider_adapters.common import AdapterError, CallContext

# Families are navigation metadata, not invented callable IDs or access claims.
FAMILIES = {
    'openai': ('GPT', 'Codex'),
    'anthropic': ('Claude', 'Mythos', 'Fable', 'Opus', 'Sonnet', 'Haiku'),
    'huggingface': ('configured open-weight checkpoints and fine-tunes',),
}
HISTORICAL_REFERENCES = {
    'openai': ('gpt-4o', 'gpt-4.1', 'codex-mini-latest'),
    'anthropic': ('claude-3-opus-20240229', 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'),
}


class ModelRegistry:
    def __init__(self):
        self.records, self.adapters, self.metrics, self.discovery_status = {}, {}, {}, {}
        self.native_key = None
        self.declarations = {}

    def register_adapter(self, adapter: ProviderAdapter):
        if adapter.name in self.adapters:
            raise ValueError('Adapter name already registered')
        if not isinstance(adapter.name, str) or not adapter.name or not callable(getattr(adapter, 'discover', None)) or not callable(getattr(adapter, 'generate', None)):
            raise ValueError('Invalid trusted provider adapter')
        self.adapters[adapter.name] = adapter

    def register(self, record):
        if not isinstance(record, ModelRecord) or record.provider not in self.adapters or not isinstance(record.model_id, str) or not 1 <= len(record.model_id) <= 300 or any(ord(c) < 32 for c in record.model_id):
            raise ValueError('Invalid model record or provider')
        self.records[record.key] = record
        return record.key

    def get(self, key):
        if key not in self.records:
            raise ValueError('Unknown model ID')
        return self.records[key]

    def observe(self, key, latency_ms, quality=None):
        if key not in self.records or latency_ms < 0 or (quality is not None and not 0 <= quality <= 1):
            raise ValueError('Invalid measured observation')
        old = self.metrics.get(key, {})
        n = old.get('calls', 0)
        item = {'calls': n + 1, 'latency_ms': (old.get('latency_ms', 0) * n + latency_ms) / (n + 1)}
        if quality is not None:
            item['quality'] = quality  # Only explicit external evaluation, never self-confidence.
        elif 'quality' in old:
            item['quality'] = old['quality']
        self.metrics[key] = item

    def refresh(self, provider, context=None):
        if provider not in self.adapters:
            raise ValueError('Unknown discovery provider')
        context = context or CallContext(time.monotonic() + 20)
        # Fail closed after failed refresh: do not route stale account access.
        try:
            rows = self.adapters[provider].discover(context)
            fresh = []
            for row in rows:
                if row.provider != provider:
                    raise ValueError('Provider returned another provider identity')
                declared = self.declarations.get(row.key)
                if declared:
                    caps = row.capabilities
                    caps = replace(caps, input_modalities=('text',), output_modalities=('text',),
                        context_window=caps.context_window or declared.get('context_window'),
                        max_output_tokens=caps.max_output_tokens or declared.get('max_output_tokens'),
                        reasoning_efforts=caps.reasoning_efforts or tuple(declared.get('reasoning_efforts', ())),
                        tags=tuple(declared.get('tags', ())), pricing=declared.get('pricing', {}),
                        extra={**caps.extra, 'api': declared.get('api', caps.extra.get('api'))})
                    row = replace(row, configured=True, capabilities=caps)
                fresh.append(row)
            if len({r.key for r in fresh}) != len(fresh):
                raise ValueError('Provider returned duplicate model IDs')
        except Exception as exc:
            for key, row in list(self.records.items()):
                if row.provider == provider and key != self.native_key:
                    self.records[key] = replace(row, availability='unavailable', access='Discovery failed; refresh required')
            self.discovery_status[provider] = {'status': 'failed', 'code': exc.code if isinstance(exc, AdapterError) else 'discovery_failed'}
            return False
        for key, row in list(self.records.items()):
            if row.provider == provider and key != self.native_key:
                self.records[key] = replace(row, availability='unavailable', access='Not returned by latest discovery')
        for row in fresh:
            if row.key == self.native_key:
                continue
            self.register(row)
            if row.configured and row.local:
                adapter = self.adapters[provider]
                s = adapter.settings
                adapter.bind(row, replace(s, provider=provider, **({'ollama_model': row.model_id} if provider == 'ollama' else {'local_server_model': row.model_id})))
        self.discovery_status[provider] = {'status': 'ok', 'models': len(fresh)}
        return True

    def public(self):
        return {'native_key': self.native_key, 'models': [r.public() for r in self.records.values()],
                'families': {p: [{'name': f, 'availability': 'requires exact account-discovered model ID'} for f in families] for p, families in FAMILIES.items()},
                'discovery': self.discovery_status, 'metrics': self.metrics,
                'modality_execution': 'text-only in Phase 1/2; capability metadata does not install a multimodal runtime'}


def external_declarations():
    text = os.environ.get('ZENITH_EXTERNAL_MODELS', '[]')
    if len(text) > 32000:
        raise ValueError('External model configuration too large')
    rows = json.loads(text)
    if not isinstance(rows, list) or len(rows) > 16:
        raise ValueError('Configure at most 16 explicit model IDs')
    allowed = {'provider', 'model_id', 'api', 'context_window', 'max_output_tokens', 'tags', 'reasoning_efforts', 'pricing'}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - allowed or row.get('provider') not in {'openai', 'anthropic', 'ollama', 'localserver'} or not isinstance(row.get('model_id'), str):
            raise ValueError('Use an explicit supported provider/model_id declaration')
        if row['provider'] == 'openai' and row.get('api') != 'responses':
            raise ValueError('Explicit Responses API compatibility required for OpenAI IDs')
        for name in ('context_window', 'max_output_tokens'):
            if name in row and (type(row[name]) is not int or not 1 <= row[name] <= 10000000):
                raise ValueError('Invalid model token limit')
        for name in ('tags', 'reasoning_efforts'):
            if name in row and (not isinstance(row[name], list) or len(row[name]) > 20 or any(not isinstance(x, str) or len(x) > 40 for x in row[name])):
                raise ValueError('Invalid model capabilities')
        prices = row.get('pricing', {})
        if not isinstance(prices, dict) or set(prices) - {'input_usd_per_million', 'output_usd_per_million', 'source'}:
            raise ValueError('Invalid sourced pricing')
        if prices and (not isinstance(prices.get('source'), str) or not prices['source'].startswith('https://')):
            raise ValueError('Pricing needs an HTTPS source reference')
        for k, v in prices.items():
            if k != 'source' and (type(v) not in {int, float} or not 0 <= v <= 1000000):
                raise ValueError('Invalid price')
        key = row['provider'] + ':' + row['model_id']
        if key in seen:
            raise ValueError('Duplicate configured model')
        seen.add(key)
    return rows


def build_registry(settings=None):
    from .provider_adapters.local_adapter import LocalAdapter
    from .provider_adapters.openai_adapter import OpenAIAdapter
    from .provider_adapters.anthropic_adapter import AnthropicAdapter
    settings = settings or Settings()
    registry = ModelRegistry()
    for name in ('huggingface', 'ollama', 'localserver', 'tiny'):
        registry.register_adapter(LocalAdapter(name, settings))
    registry.register_adapter(OpenAIAdapter())
    registry.register_adapter(AnthropicAdapter())
    native = os.getenv('ZENITH_NATIVE_PROVIDER', 'huggingface')
    if native not in {'huggingface', 'ollama', 'localserver', 'tiny'}:
        raise ValueError('Native provider must use an existing local Zenith runtime')
    local_settings = replace(settings, provider=native)
    identifier = local_settings.model_name
    record = ModelRecord(native, identifier, 'configured', configured=True, local=True,
        capabilities=ModelCapabilities(context_window=settings.context_tokens + settings.max_new_tokens, max_output_tokens=settings.max_new_tokens,
            tags=('coding', 'general'), extra={'revision': settings.revision, 'adapter_selected': bool(settings.adapter)}),
        access='Existing local configuration; load validated by original provider', provenance='Existing Zenith Settings')
    registry.native_key = registry.register(record)
    registry.adapters[native].bind(record, local_settings)
    for provider, ids in HISTORICAL_REFERENCES.items():
        for identifier in ids:
            registry.register(ModelRecord(provider, identifier, provenance='Historical reference; no current availability claim'))
    for row in external_declarations():
        record = ModelRecord(row['provider'], row['model_id'], configured=True, local=row['provider'] in {'ollama', 'localserver'})
        if record.key == registry.native_key:
            raise ValueError('Native model cannot be overridden by external declarations')
        registry.declarations[record.key] = row
        registry.register(record)
    return registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='list', choices=('list', 'discover'))
    parser.add_argument('--provider', choices=('openai', 'anthropic', 'ollama', 'localserver', 'huggingface'))
    parser.add_argument('--query', default='')
    args = parser.parse_args()
    registry = build_registry()
    ok = True
    if args.action == 'discover':
        if not args.provider:
            parser.error('Choose one provider explicitly; discovery never fans out automatically')
        if args.provider == 'huggingface':
            # Existing public metadata discovery; never installs or enables models.
            from .discovery import Discovery
            print(json.dumps(Discovery().search(source='huggingface', q=args.query), indent=2))
            return 0
        ok = registry.refresh(args.provider)
    print(json.dumps(registry.public(), indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
