"""Decode actual Qwen tool-call output; this module never executes a tool."""
import json
import re
import uuid
from jsonschema.validators import validator_for
from .chat_contract import plain_json


class InvalidModelOutput(ValueError):
    pass


def parse_output(text, request):
    calls, remaining = [], text
    definitions = {t.function.name: t.function.parameters for t in request.tools or []}
    spans = list(re.finditer(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL))
    if '<tool_call>' in text or '</tool_call>' in text:
        remaining = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
        if not spans or '<tool_call>' in remaining or '</tool_call>' in remaining or len(spans) > 16:
            raise InvalidModelOutput('Incomplete tool output')
        if request.tool_choice == 'none':
            raise InvalidModelOutput('Model called a disabled tool')
        for span in spans:
            try:
                raw = plain_json(span.group(1))
                if not isinstance(raw, dict) or set(raw) != {'name', 'arguments'} or raw['name'] not in definitions or not isinstance(raw['arguments'], dict):
                    raise ValueError('Unrecognized function call')
                validator_for(definitions[raw['name']])(definitions[raw['name']]).validate(raw['arguments'])
                if isinstance(request.tool_choice, dict) and raw['name'] != request.tool_choice['function']['name']:
                    raise ValueError('Wrong forced function')
            except Exception as exc:
                raise InvalidModelOutput('Tool output failed the requested schema') from exc
            calls.append({'id': 'call_' + uuid.uuid4().hex, 'type': 'function',
                          'function': {'name': raw['name'], 'arguments': json.dumps(raw['arguments'], ensure_ascii=False, allow_nan=False)}})
        if not request.parallel_tool_calls and len(calls) > 1:
            raise InvalidModelOutput('Parallel tool calls are disabled')
    if not calls and (request.tool_choice == 'required' or isinstance(request.tool_choice, dict)):
        raise InvalidModelOutput('Model did not produce the required tool call')
    content = remaining.strip()
    if request.response_format and not calls:
        try:
            value = plain_json(content)
            if not isinstance(value, dict):
                raise ValueError('Expected JSON object')
            if request.response_format['type'] == 'json_schema':
                schema = request.response_format['json_schema']['schema']
                validator_for(schema)(schema).validate(value)
        except Exception as exc:
            raise InvalidModelOutput('Response failed the requested JSON format') from exc
    if not content and not calls:
        raise InvalidModelOutput('Model produced no answer')
    return {'role': 'assistant', 'content': content or None, **({'tool_calls': calls} if calls else {})}
