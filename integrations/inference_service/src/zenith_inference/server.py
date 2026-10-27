"""Private, authenticated OpenAI chat subset over Zenith's unchanged checkpoint."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
import queue
import time
import uuid

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from zenith_integrations.shared.http_boundary import PrivateAPIBoundary
from .chat_contract import ChatRequest
from .limits import Admission,ModelBusy,Cancellation, ContextExceeded, InferenceCancelled
from .tool_calls import InvalidModelOutput, parse_output

logger = logging.getLogger('zenith.inference')


def error_response(status, code, request_id):
    messages = {'invalid_request': 'Request is unsupported or exceeds the configured budget',
                'invalid_model_output': 'Model output did not satisfy the requested tool or response schema',
                'deadline_exceeded': 'Inference was cancelled or its deadline expired',
                'inference_unavailable': 'Verified inference is unavailable'}
    return JSONResponse({'error': {'message': messages[code], 'type': code, 'code': code,
                                  'request_id': request_id}}, status_code=status)


def failure(exc, request_id):
    if isinstance(exc, ContextExceeded):
        return error_response(400, 'invalid_request', request_id)
    if isinstance(exc, InvalidModelOutput):
        return error_response(502, 'invalid_model_output', request_id)
    if isinstance(exc, InferenceCancelled):
        return error_response(504, 'deadline_exceeded', request_id)
    return error_response(503, 'inference_unavailable', request_id)


class Run:
    def __init__(self, backend, request, gate, identity):
        self.request, self.backend, self.gate, self.identity = request, backend, gate, identity
        self.id = 'chatcmpl-' + uuid.uuid4().hex
        self.created, self.started = int(time.time()), time.monotonic()
        self.cancel = Cancellation(backend.limits.deadline_seconds)
        self.chunks = queue.Queue(maxsize=32)
        self.future = None
        self.closed = False

    def start(self):
        # Buffer tool/schema requests until the complete result is validated.
        emit = self.emit if self.request.stream and not self.request.tools and not self.request.response_format else None
        self.future = asyncio.get_running_loop().run_in_executor(None, self.backend.complete, self.request, self.cancel, emit)

    def emit(self, value):
        while not self.cancel.cancelled():
            try:
                self.chunks.put(value, timeout=0.05)
                return
            except queue.Full:
                continue
        self.cancel.check()

    async def close(self):
        if self.closed:
            return
        self.cancel.event.set()
        # Do not release model admission until its worker actually returns.
        with anyio.CancelScope(shield=True):
            if self.future:
                with suppress(Exception):
                    await asyncio.shield(self.future)
            if not self.closed:
                self.closed = True
                self.gate.release()
                logger.info(json.dumps({'event': 'inference.finished', 'request_id': self.id,
                    'service': self.identity.name, 'duration_ms': round((time.monotonic() - self.started) * 1000),
                    'worker_finished': self.future is None or self.future.done()}))

    def result(self):
        result = self.future.result()
        message = parse_output(result.text, self.request)
        if message.get('tool_calls') and result.finish_reason != 'stop':
            raise InvalidModelOutput('Truncated tool output cannot authorize a call')
        finish = 'tool_calls' if message.get('tool_calls') else result.finish_reason
        usage = {'prompt_tokens': result.prompt_tokens, 'completion_tokens': result.completion_tokens,
                 'total_tokens': result.prompt_tokens + result.completion_tokens}
        return message, finish, usage

    def chunk(self, delta, finish=None, usage=None):
        return {'id': self.id, 'object': 'chat.completion.chunk', 'created': self.created, 'model': 'zenith',
                'choices': [] if usage is not None else [{'index': 0, 'delta': delta, 'finish_reason': finish}],
                **({'usage': usage} if usage is not None else {})}


class OwnedStreamingResponse(StreamingResponse):
    def __init__(self, *args, run, **kwargs):
        super().__init__(*args, **kwargs)
        self.run = run

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                close = getattr(self.body_iterator, 'aclose', None)
                try:
                    if close:
                        await close()
                finally:
                    await self.run.close()


def create_app(backend, auth, allowed_hosts=('127.0.0.1', 'localhost', '::1'),queue_size=0):
    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            close = getattr(backend, 'close', None)
            if close:
                with anyio.CancelScope(shield=True):
                    await anyio.to_thread.run_sync(close)
    app = FastAPI(title='Zenith inference', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(PrivateAPIBoundary, allowed_hosts=tuple(allowed_hosts))
    gate = Admission(queue_size,backend.limits.deadline_seconds)
    app.state.backend, app.state.gate = backend, gate

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return error_response(400, 'invalid_request', 'validation-' + uuid.uuid4().hex)

    @app.get('/healthz')
    async def health(request: Request):
        auth.authenticate(request, 'inference.read')
        return {'status': 'ok', 'model_loaded': backend.model is not None, 'live_execution': False}

    @app.get('/readyz')
    async def readiness(request: Request):
        auth.authenticate(request, 'inference.read')
        ready = backend.model is not None and backend.identity_hash is not None
        return JSONResponse({'ready': ready, 'identity_sha256': backend.identity_hash,
            'context_tokens': backend.limits.context_tokens,
            'architectural_context_tokens': getattr(getattr(backend.model, 'config', None), 'max_position_embeddings', None),
            'max_output_tokens': backend.limits.max_output_tokens}, status_code=200 if ready else 503)

    @app.get('/v1/models')
    async def models(request: Request):
        principal = auth.authenticate(request, 'inference.read')
        models = [{'id': 'zenith', 'object': 'model', 'created': 0, 'owned_by': 'zenith'}] if 'zenith' in principal.models else []
        return {'object': 'list', 'data': models}

    def generation_identity(request: Request):
        return auth.authenticate(request, 'inference.generate', 'zenith')

    @app.post('/v1/chat/completions')
    async def completions(request: Request, body: ChatRequest, principal=Depends(generation_identity)):
        if body.maximum and body.maximum > backend.limits.max_output_tokens:
            return error_response(400, 'invalid_request', 'admission-' + uuid.uuid4().hex)
        async def disconnected():
            while True:
                message = await request.receive()
                if message['type'] == 'http.disconnect':
                    return
        disconnect = asyncio.create_task(disconnected())
        async def close_disconnect():
            disconnect.cancel()
            with suppress(asyncio.CancelledError):await disconnect
        try:
            await gate.acquire(disconnect)
        except ModelBusy:
            await close_disconnect()
            raise HTTPException(429, 'Model is busy', headers={'Retry-After': '1'}) from None
        except BaseException as exc:
            await close_disconnect()
            if isinstance(exc,InferenceCancelled):return failure(exc,'admission-'+uuid.uuid4().hex)
            raise
        run = Run(backend, body, gate, principal)
        try:
            run.start()
        except BaseException:
            await run.close()
            await close_disconnect()
            raise
        if body.stream:
            # The streaming response takes ownership of receive from here.
            await close_disconnect()
            def event(value):
                return 'data: ' + json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n\n'
            async def stream():
                try:
                    yield event(run.chunk({'role': 'assistant', 'content': ''}))
                    sent = False
                    while not run.future.done() or not run.chunks.empty():
                        run.cancel.check()
                        try:
                            chunk = run.chunks.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue
                        sent = True
                        yield event(run.chunk({'content': chunk}))
                    message, finish, usage = run.result()
                    if not sent and message['content']:
                        yield event(run.chunk({'content': message['content']}))
                    if message.get('tool_calls'):
                        yield event(run.chunk({'tool_calls': [{'index': i, **call} for i, call in enumerate(message['tool_calls'])]}))
                    yield event(run.chunk({}, finish))
                    if body.stream_options and body.stream_options.get('include_usage'):
                        yield event(run.chunk({}, usage=usage))
                    yield 'data: [DONE]\n\n'
                except Exception as exc:
                    response = failure(exc, run.id)
                    yield 'data: ' + response.body.decode() + '\n\n'
                    yield 'data: [DONE]\n\n'
                finally:
                    await run.close()
            return OwnedStreamingResponse(stream(), run=run, media_type='text/event-stream',
                                          headers={'X-Request-ID': run.id, 'X-Accel-Buffering': 'no'})
        try:
            while not run.future.done():
                completed, _ = await asyncio.wait((run.future, disconnect), timeout=0.05,
                                                  return_when=asyncio.FIRST_COMPLETED)
                if disconnect in completed or run.cancel.cancelled():
                    run.cancel.event.set()
                if disconnect.done() and not run.future.done():
                    # Do not spin on a completed disconnect task while the
                    # cooperative model worker drains its current token.
                    await asyncio.wait((run.future,), timeout=0.05)
            message, finish, usage = run.result()
            return JSONResponse({'id': run.id, 'object': 'chat.completion', 'created': run.created, 'model': 'zenith',
                'choices': [{'index': 0, 'message': message, 'finish_reason': finish}], 'usage': usage},
                headers={'X-Request-ID': run.id})
        except Exception as exc:
            return failure(exc, run.id)
        finally:
            await close_disconnect()
            await run.close()
    return app
