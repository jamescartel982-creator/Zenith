"""Strict text/tool chat contract. Unsupported model features fail explicitly."""
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator
from jsonschema.validators import validator_for

NAME = re.compile(r'[a-zA-Z0-9_-]{1,64}')


def plain_json(text):
    def duplicate(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON property')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=duplicate,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON')))


def validate_schema(schema):
    if not isinstance(schema, dict) or len(json.dumps(schema)) > 65536:
        raise ValueError('Tool schemas must be bounded JSON objects')
    visited = 0
    def walk(value, depth=0, references=()):
        nonlocal visited
        visited += 1
        if depth > 24 or visited > 4096:
            raise ValueError('JSON Schema is too deeply nested')
        if isinstance(value, dict):
            for key, item in value.items():
                if key == '$ref':
                    if not isinstance(item, str) or not item.startswith('#/') or item in references:
                        raise ValueError('Only bounded acyclic local schema references are allowed')
                    target = schema
                    try:
                        for part in item[2:].split('/'):
                            target = target[part.replace('~1', '/').replace('~0', '~')]
                    except (KeyError, TypeError) as exc:
                        raise ValueError('Unresolved local schema reference') from exc
                    walk(target, depth + 1, references + (item,))
                if key in {'$dynamicRef', '$recursiveRef', '$id', '$dynamicAnchor', 'pattern', 'patternProperties'}:
                    raise ValueError('Dynamic references and regular-expression schemas are unsupported')
                if key == '$schema' and (not isinstance(item, str) or item not in {'https://json-schema.org/draft/2020-12/schema', 'http://json-schema.org/draft-07/schema#'}):
                    raise ValueError('Unsupported schema dialect')
                walk(item, depth + 1, references)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1, references)
    walk(schema)
    try:
        validator_for(schema).check_schema(schema)
    except Exception as exc:
        raise ValueError('Invalid JSON Schema') from exc


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class FunctionCall(StrictModel):
    name: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    arguments: str = Field(max_length=65536)

    @model_validator(mode='after')
    def arguments_object(self):
        if not isinstance(plain_json(self.arguments), dict):
            raise ValueError('Function arguments must encode a JSON object')
        return self


class ToolCall(StrictModel):
    id: str = Field(min_length=1, max_length=128, pattern=r'^[a-zA-Z0-9_-]+$')
    type: Literal['function'] = 'function'
    function: FunctionCall


class Message(StrictModel):
    role: Literal['system', 'user', 'assistant', 'tool']
    content: str | list[dict[str, Any]] | None = None
    tool_calls: list[ToolCall] | None = Field(default=None, max_length=16)
    tool_call_id: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, pattern=r'^[a-zA-Z0-9_-]{1,64}$')

    @model_validator(mode='after')
    def text_and_roles(self):
        if isinstance(self.content, list):
            if any(set(v) != {'type', 'text'} or v.get('type') != 'text' or not isinstance(v.get('text'), str) for v in self.content):
                raise ValueError('Only text content is supported by this checkpoint')
            self.content = ''.join(v['text'] for v in self.content)
        if self.content is None and not (self.role == 'assistant' and self.tool_calls):
            raise ValueError('Text content is required')
        if self.tool_calls and self.role != 'assistant':
            raise ValueError('Only assistant messages can contain tool calls')
        if (self.role == 'tool') != bool(self.tool_call_id):
            raise ValueError('Tool results require their original call id')
        return self


class FunctionSpec(StrictModel):
    name: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    description: str | None = Field(default=None, max_length=16000)
    parameters: dict[str, Any] = Field(default_factory=lambda: {'type': 'object', 'properties': {}})
    strict: StrictBool | None = None

    @model_validator(mode='after')
    def schema_valid(self):
        validate_schema(self.parameters)
        return self


class ToolSpec(StrictModel):
    type: Literal['function'] = 'function'
    function: FunctionSpec


class ChatRequest(StrictModel):
    model: Literal['zenith'] = 'zenith'
    messages: list[Message] = Field(min_length=1, max_length=256)
    max_tokens: StrictInt | None = Field(default=None, ge=1, le=4096)
    max_completion_tokens: StrictInt | None = Field(default=None, ge=1, le=4096)
    temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    top_p: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    stream: StrictBool = False
    stream_options: dict[str, StrictBool] | None = None
    tools: list[ToolSpec] | None = Field(default=None, max_length=64)
    tool_choice: str | dict[str, Any] | None = None
    parallel_tool_calls: StrictBool = True
    reasoning_effort: Literal['none'] | None = None
    response_format: dict[str, Any] | None = None
    n: Literal[1] = 1
    stop: str | list[str] | None = None

    @model_validator(mode='after')
    def complete_contract(self):
        try:
            json.dumps(self.model_dump(), allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise ValueError('Non-finite JSON values are unsupported') from exc
        if self.max_tokens is not None and self.max_completion_tokens is not None:
            raise ValueError('Choose one output-token limit')
        if self.stop is not None:
            raise ValueError('Custom stop strings are unsupported; native EOS and output limits are enforced')
        if self.stream_options is not None and set(self.stream_options) - {'include_usage'}:
            raise ValueError('Unsupported streaming option')
        names = [t.function.name for t in self.tools or []]
        if len(names) != len(set(names)):
            raise ValueError('Tool names must be unique')
        choice = self.tool_choice
        if isinstance(choice, str) and choice not in {'auto', 'none', 'required'}:
            raise ValueError('Unsupported tool choice')
        if isinstance(choice, dict):
            if set(choice) != {'type', 'function'} or choice['type'] != 'function' or not isinstance(choice['function'], dict) or set(choice['function']) != {'name'} or choice['function']['name'] not in names:
                raise ValueError('Forced tool must be one of the supplied tools')
        if not names and choice not in (None, 'auto', 'none'):
            raise ValueError('No tool is available')
        pending, seen = set(), set()
        for message in self.messages:
            if message.role == 'tool':
                if message.tool_call_id not in pending:
                    raise ValueError('Orphan or repeated tool result')
                pending.remove(message.tool_call_id)
            else:
                if pending:
                    raise ValueError('Every tool call needs its original result before the next turn')
                for call in message.tool_calls or []:
                    if call.id in seen:
                        raise ValueError('Tool call ids must be unique')
                    pending.add(call.id)
                    seen.add(call.id)
        if pending or self.messages[-1].role == 'assistant':
            raise ValueError('Supply completed tool results or a new user turn')
        if self.response_format:
            fmt = self.response_format
            if fmt.get('type') == 'json_object' and set(fmt) == {'type'}:
                pass
            elif fmt.get('type') == 'json_schema' and set(fmt) == {'type', 'json_schema'}:
                item = fmt['json_schema']
                if not isinstance(item, dict) or set(item) - {'name', 'strict', 'schema', 'description'} or 'schema' not in item:
                    raise ValueError('Invalid response schema')
                validate_schema(item['schema'])
            else:
                raise ValueError('Unsupported response format')
        return self

    @property
    def maximum(self):
        return self.max_tokens or self.max_completion_tokens

    def native_messages(self):
        values = []
        for message in self.messages:
            row = message.model_dump(exclude_none=True)
            for call in row.get('tool_calls') or []:
                call['function']['arguments'] = plain_json(call['function']['arguments'])
            if row.get('content') is None:
                row['content'] = ''
            values.append(row)
        if values[0]['role'] != 'system':
            values.insert(0, {'role':'system','content':'You are Zenith, a helpful AI assistant.'})
        constraints = []
        if self.tool_choice == 'required':
            constraints.append('You must call one of the provided functions in this response.')
        elif isinstance(self.tool_choice, dict):
            constraints.append('Call the provided function '+self.tool_choice['function']['name']+' in this response.')
        if self.response_format:
            constraints.append('Return only a valid JSON object without Markdown wrappers.')
            if self.response_format['type'] == 'json_schema':
                constraints.append('The response must satisfy this JSON Schema: '+json.dumps(self.response_format['json_schema']['schema']))
        if constraints:
            values[0] = {**values[0], 'content':values[0]['content']+'\n'+'\n'.join(constraints)}
        return values
