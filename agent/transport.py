"""Bounded framing for local model HTTP streams.

Framing alone does not establish success. Each provider must observe its own
completion marker before the application may persist an answer.
"""
import json


MAX_FRAME_BYTES = 1024 * 1024
MAX_STREAM_BYTES = 8 * MAX_FRAME_BYTES


class ProviderProtocolError(RuntimeError):
    """The model server returned an incomplete or invalid response."""


def stream_lines(response, cancel):
    """Decode bounded UTF-8 lines, including CR, LF and split CRLF boundaries.

    A one-byte Requests read avoids waiting for a 512-byte buffer to fill on
    unchunked HTTP servers. Limits apply before decoding or JSON parsing.
    """
    pending = bytearray()
    total = 0
    skip_lf = False
    first_line = True

    def decode():
        nonlocal first_line
        try:
            line = pending.decode('utf-8-sig' if first_line else 'utf-8')
        except UnicodeDecodeError as exc:
            raise ProviderProtocolError('Model stream contains invalid UTF-8') from exc
        first_line = False
        pending.clear()
        return line

    for chunk in response.iter_content(chunk_size=1):
        if cancel.is_set():
            return
        total += len(chunk)
        if total > MAX_STREAM_BYTES:
            raise ProviderProtocolError('Model stream exceeded the transport byte limit')
        for byte in chunk:
            if skip_lf:
                skip_lf = False
                if byte == 10:
                    continue
            if byte in (10, 13):
                yield decode()
                skip_lf = byte == 13
            else:
                pending.append(byte)
                if len(pending) > MAX_FRAME_BYTES:
                    raise ProviderProtocolError('Model stream line exceeded the frame limit')
    if pending and not cancel.is_set():
        yield decode()


def json_object(payload):
    try:
        value = json.loads(payload)
    except (ValueError, RecursionError) as exc:
        raise ProviderProtocolError('Model server returned invalid JSON') from exc
    if not isinstance(value, dict):
        raise ProviderProtocolError('Model server returned a non-object response')
    if value.get('error'):
        # An upstream error can include prompts, credentials, or host paths.
        raise ProviderProtocolError('Model server reported a generation error')
    return value


def ndjson_objects(response, cancel):
    for line in stream_lines(response, cancel):
        if line.strip():
            yield json_object(line)


def sse_payloads(response, cancel):
    """Dispatch complete SSE events; an EOF without a blank line is incomplete."""
    data = []
    size = 0
    for line in stream_lines(response, cancel):
        if not line:
            if data:
                yield '\n'.join(data)
            data = []
            size = 0
            continue
        if line.startswith(':'):
            continue
        field, separator, value = line.partition(':')
        if field != 'data':
            continue
        if separator and value.startswith(' '):
            value = value[1:]
        size += len(value.encode('utf-8')) + 1
        if size > MAX_FRAME_BYTES:
            raise ProviderProtocolError('Model SSE event exceeded the frame limit')
        data.append(value)
    if data and not cancel.is_set():
        raise ProviderProtocolError('Model SSE stream ended inside an event')


def final_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ProviderProtocolError('Model server returned no final text; check its model and output budget')
    return value


def delta_text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ProviderProtocolError('Model server returned an invalid text delta')
    return value
