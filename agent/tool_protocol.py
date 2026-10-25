"""Bounded explicit tool proposals; no arbitrary shell or executable package data."""
from dataclasses import dataclass
import json

from .execution import CAPABILITIES
from .platform_repository import canonical


@dataclass(frozen=True)
class ToolCall:
    tool: str
    arguments_json: str

    @property
    def arguments(self):
        # Each consumer gets its own snapshot; post-review mutation cannot alias it.
        return json.loads(self.arguments_json)

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict) or set(value) != {'tool', 'arguments'}:
            raise ValueError('A tool call needs exactly tool and arguments')
        tool, arguments = value['tool'], value['arguments']
        if not isinstance(tool, str) or tool not in CAPABILITIES or not isinstance(arguments, dict):
            raise ValueError('Unknown capability or invalid argument object')
        if tool in {'tcp-connect', 'tls-certificate'}:
            if set(arguments) != {'host', 'port'} or not isinstance(arguments['host'], str) or len(arguments['host']) > 253 or type(arguments['port']) is not int or not 1 <= arguments['port'] <= 65535:
                raise ValueError('Network tools need a bounded literal host and integer port')
        elif set(arguments) != {'text'} or not isinstance(arguments['text'], str) or len(arguments['text']) > 12000:
            raise ValueError('Offline tools accept only bounded pasted text')
        return cls(tool, canonical(arguments, 16000))


def parse_plan(steps, max_steps=8):
    if not isinstance(steps, list) or not 1 <= len(steps) <= max_steps:
        raise ValueError('A plan needs one to eight explicit diagnostic steps')
    return [ToolCall.parse(step) for step in steps]
