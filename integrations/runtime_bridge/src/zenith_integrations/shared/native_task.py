"""Exact chat intent and cancellation cleanup shared by native runtime adapters."""
import asyncio
import hashlib

from .native_http import NativeRefused


def chat_scope(payload, operation):
    if operation not in {'chat', 'support'} or not isinstance(payload, dict) or set(payload) != {'message', 'conversation_id'}:
        raise NativeRefused('only_explicit_scoped_chat_is_enabled')
    message, conversation = payload['message'], payload['conversation_id']
    if not isinstance(message, str) or not message.strip() or len(message) > 16000:
        raise NativeRefused('invalid_chat_message')
    if not isinstance(conversation, str) or not conversation or len(conversation) > 128:
        raise NativeRefused('invalid_chat_conversation')
    return {'conversation_id': conversation, 'message_sha256': hashlib.sha256(message.encode()).hexdigest()}


async def finish_cleanup(coroutine):
    """Cancellation does not acknowledge termination until native cleanup finishes."""
    task = asyncio.create_task(coroutine)
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()
