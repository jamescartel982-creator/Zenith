"""Optional official Anthropic Messages API; exact account model discovery."""
import os
from .common import AdapterError, final_completion, request_json, text_messages
from ..model_capabilities import ModelCapabilities, ModelRecord


def supported(value):
    return isinstance(value, dict) and value.get('supported') is True


class AnthropicAdapter:
    name = 'anthropic'

    def __init__(self, request=None):
        self.request = request

    def _json(self, method, path, context, payload=None, params=None):
        key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not key:
            raise AdapterError('credential_missing')
        return request_json(method, 'https://api.anthropic.com/v1/' + path, context,
            headers={'x-api-key': key, 'anthropic-version': '2026-10-21', 'Content-Type': 'application/json'},
            payload=payload, params=params, request=self.request)

    def discover(self, context):
        result, cursor, seen = [], None, set()
        for _ in range(20):
            data = self._json('GET', 'models', context, params={'limit': 100, **({'after_id': cursor} if cursor else {})})
            if not isinstance(data.get('data'), list):
                raise AdapterError('invalid_model_list')
            for row in data['data']:
                if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                    raise AdapterError('invalid_model_list')
                caps = row.get('capabilities') or {}
                if not isinstance(caps, dict):
                    raise AdapterError('invalid_model_capabilities')
                modalities = ('text',) + (('image',) if supported(caps.get('image_input')) else ()) + (('pdf',) if supported(caps.get('pdf_input')) else ())
                efforts = caps.get('effort') or {}
                reasoning = tuple(e for e in ('low', 'medium', 'high', 'xhigh', 'max') if isinstance(efforts, dict) and supported(efforts.get(e)))
                lifecycle = row.get('lifecycle', 'unknown')
                result.append(ModelRecord(self.name, row['id'], 'unavailable' if lifecycle == 'retired' else 'listed',
                    lifecycle=lifecycle, family=row.get('line'), access='Account-visible; an inference request can still be denied',
                    capabilities=ModelCapabilities(input_modalities=modalities, context_window=row.get('max_input_tokens'),
                        max_output_tokens=row.get('max_tokens'), reasoning_efforts=reasoning,
                        extra={'api': 'messages', 'provider_capabilities': caps, 'retirement_date': row.get('retires_at')}),
                    provenance='Anthropic GET /v1/models'))
            if data.get('has_more') is False:
                return result
            cursor = data.get('last_id')
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise AdapterError('invalid_pagination')
            seen.add(cursor)
        raise AdapterError('model_list_page_limit')

    def generate(self, record, messages, context):
        used = text_messages(messages)
        payload = {'model': record.model_id, 'max_tokens': context.max_output_tokens,
                   'messages': [m for m in used if m['role'] != 'system']}
        system = '\n\n'.join(m['content'] for m in used if m['role'] == 'system')
        if system:
            payload['system'] = system
        if context.effort and context.effort in record.capabilities.reasoning_efforts:
            payload['output_config'] = {'effort': context.effort}
        data = self._json('POST', 'messages', context, payload)
        if data.get('stop_reason') != 'end_turn' or data.get('model', record.model_id) != record.model_id:
            raise AdapterError('incomplete_or_different_model')
        blocks = data.get('content')
        if not isinstance(blocks, list) or any(not isinstance(b, dict) or b.get('type') != 'text' or not isinstance(b.get('text'), str) for b in blocks):
            raise AdapterError('unexpected_tool_or_output')
        from ..providers import token_usage
        counts = data.get('usage') or {}
        # Cache-read/cache-write tokens are additional input, not free tokens.
        incoming = counts.get('input_tokens')
        if type(incoming) is int:
            incoming += counts.get('cache_read_input_tokens', 0) + counts.get('cache_creation_input_tokens', 0)
        return final_completion(''.join(b['text'] for b in blocks), used,
            token_usage(incoming, counts.get('output_tokens'), finish_reason='stop'), 'stop')
