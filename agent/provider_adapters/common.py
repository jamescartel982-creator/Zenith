"""Bounded HTTP JSON with sanitized errors, fixed upstreams and no redirects."""
import json
import time
from dataclasses import dataclass, field
from threading import Event
import requests


class AdapterError(RuntimeError):
    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.code, self.retryable = code, retryable


class Cancelled(AdapterError):
    def __init__(self):
        super().__init__('request_cancelled')


@dataclass
class CallContext:
    deadline: float
    cancel: Event = field(default_factory=Event)
    max_output_tokens: int = 256
    effort: str | None = None
    clock: object = time.monotonic

    def check(self):
        if self.cancel.is_set():
            raise Cancelled()
        if self.clock() >= self.deadline:
            raise AdapterError('deadline_exceeded')

    def remaining(self):
        self.check()
        return self.deadline - self.clock()


class DeadlineCancel:
    """Child stream owns its close signal; it cannot cancel the parent request."""
    def __init__(self, context):
        self.context, self.closed = context, False

    def is_set(self):
        return self.closed or self.context.cancel.is_set() or self.context.clock() >= self.context.deadline

    def set(self):
        self.closed = True


def request_json(method, url, context, *, headers=None, payload=None, params=None, request=None):
    context.check()
    remaining = context.remaining()
    try:
        # Read timeout bounds idle I/O; the deadline is checked between chunks.
        # There are no detached request threads or automatic billable retries.
        with (request or requests.request)(method, url, headers=headers, json=payload, params=params,
                timeout=(min(5, remaining), min(10, remaining)), stream=True, allow_redirects=False) as response:
            context.check()
            status = response.status_code
            if status != 200:
                raise AdapterError('access_denied' if status in {401, 403, 404} else 'provider_http_error',
                                   status in {408, 429, 500, 502, 503, 504})
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=4096):
                context.check()
                size += len(chunk)
                if size > 8 * 1024 * 1024:
                    raise AdapterError('response_too_large')
                chunks.append(chunk)
        context.check()
        data = json.loads(b''.join(chunks))
        if not isinstance(data, dict) or data.get('error'):
            raise AdapterError('invalid_provider_response')
        return data
    except requests.RequestException:
        # Never echo upstream bodies, URLs containing secrets, headers or prompts.
        raise AdapterError('provider_connection_failed', retryable=True) from None
    except (ValueError, UnicodeError):
        raise AdapterError('invalid_provider_json') from None


def text_messages(messages):
    if not isinstance(messages, list) or not 1 <= len(messages) <= 100:
        raise ValueError('Provide one to 100 text messages')
    for row in messages:
        if not isinstance(row, dict) or set(row) != {'role', 'content'} or row['role'] not in {'system', 'user', 'assistant'} or not isinstance(row['content'], str):
            raise ValueError('This adapter accepts text messages only; tools and modalities require a compatible runtime')
    if sum(len(row['content'].encode('utf-8')) for row in messages) > 1024 * 1024:
        raise ValueError('Message payload exceeds one MiB')
    return [dict(row) for row in messages]


def final_completion(text, messages, usage=None, finish_reason=None):
    from ..model_capabilities import Completion
    if not isinstance(text, str) or not text.strip() or len(text) > 150000:
        raise AdapterError('invalid_text_completion')
    return Completion(text.strip(), messages, usage, finish_reason)
