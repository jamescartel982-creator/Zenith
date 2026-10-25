"""Optional official OpenAI Responses API; no built-in tools or stored responses."""
import os
from datetime import date
from .common import AdapterError, final_completion, request_json, text_messages
from ..model_capabilities import ModelCapabilities, ModelRecord


class OpenAIAdapter:
    name = 'openai'

    def __init__(self, request=None):
        self.request = request

    def _json(self, method, path, context, payload=None):
        key = os.environ.get('OPENAI_API_KEY', '')
        if not key:
            raise AdapterError('credential_missing')
        return request_json(method, 'https://api.openai.com/v1/' + path, context,
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, payload=payload, request=self.request)

    def discover(self, context):
        data = self._json('GET', 'models', context)
        if not isinstance(data.get('data'), list):
            raise AdapterError('invalid_model_list')
        result = []
        for row in data['data'][:10000]:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                raise AdapterError('invalid_model_list')
            shutdown = row.get('shutdown_date')
            retired = bool(shutdown and shutdown <= date.today().isoformat())
            result.append(ModelRecord(self.name, row['id'], 'unavailable' if retired else 'listed',
                lifecycle='retired' if retired else 'unknown', access='Account-visible; inference access and endpoint compatibility not yet verified',
                capabilities=ModelCapabilities(input_modalities=(), output_modalities=(), extra={'shutdown_date': shutdown}),
                provenance='OpenAI GET /v1/models'))
        return result

    def generate(self, record, messages, context):
        used = text_messages(messages)
        if record.capabilities.extra.get('api') != 'responses':
            raise AdapterError('responses_compatibility_not_declared')
        payload = {'model': record.model_id, 'input': used, 'max_output_tokens': context.max_output_tokens, 'store': False}
        if context.effort and context.effort in record.capabilities.reasoning_efforts:
            payload['reasoning'] = {'effort': context.effort}
        data = self._json('POST', 'responses', context, payload)
        if data.get('status') != 'completed' or data.get('model', record.model_id) != record.model_id:
            # Aliases may resolve to a snapshot; callers must configure its exact ID.
            raise AdapterError('incomplete_or_different_model')
        output = data.get('output')
        if not isinstance(output, list):
            raise AdapterError('invalid_response_output')
        pieces = []
        for item in output:
            if not isinstance(item, dict):
                raise AdapterError('invalid_response_output')
            if item.get('type') == 'reasoning':
                continue  # Do not expose hidden reasoning.
            if item.get('type') != 'message' or item.get('role') != 'assistant':
                raise AdapterError('unexpected_tool_or_output')
            for block in item.get('content', []):
                if block.get('type') != 'output_text' or not isinstance(block.get('text'), str):
                    raise AdapterError('unexpected_output_block')
                pieces.append(block['text'])
        from ..providers import token_usage
        usage = data.get('usage') or {}
        return final_completion(''.join(pieces), used, token_usage(usage.get('input_tokens'), usage.get('output_tokens'), finish_reason='stop'), 'stop')
