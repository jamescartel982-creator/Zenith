"""Optional task API sharing the current server authentication and security headers."""
import asyncio
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .runtime import PlatformRuntime
from .task_store import CapacityError, LeaseLost


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['chat', 'diagnostics']
    message: str | None = Field(default=None, min_length=1, max_length=12000)
    steps: list[dict] | None = Field(default=None, min_length=1, max_length=8)
    conversation_id: str | None = Field(default=None, max_length=36)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    approved: bool


class PlatformBodyLimit:
    """Bound new write requests before JSON parsing, including chunked bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope.get('path', '').startswith('/api/platform/') or scope['method'] not in {'POST', 'PUT', 'PATCH'}:
            return await self.app(scope, receive, send)
        chunks = []
        async def read():
            total = 0
            for _ in range(128):
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return False
                part = message.get('body', b'')
                total += len(part)
                if total > 65536:
                    return False
                chunks.append(part)
                if not message.get('more_body', False):
                    return True
            return False
        try:
            allowed = await asyncio.wait_for(read(), timeout=5)
        except asyncio.TimeoutError:
            return await JSONResponse({'detail': 'Request body timed out'}, status_code=408)(scope, receive, send)
        if not allowed:
            return await JSONResponse({'detail': 'Platform request body exceeds its budget'}, status_code=413)(scope, receive, send)
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)


def install_platform(app, agent, config, authenticate, signed_in):
    service = PlatformRuntime(agent, config)
    app.state.platform = service
    router = APIRouter(prefix='/api/platform', dependencies=[Depends(authenticate)])

    def call(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, 'Task or approval not found') from exc
        except CapacityError as exc:
            raise HTTPException(429, str(exc), headers={'Retry-After': '2'}) from exc
        except LeaseLost as exc:
            raise HTTPException(409, 'Task state changed; refresh before retrying') from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(503, 'Task storage or worker unavailable') from exc

    def actor(request: Request, user=Depends(signed_in)):
        return call(service.permissions.resolve, request.cookies.get('zenith_login', ''))

    @router.get('/status')
    def status(context=Depends(actor)):
        return service.status()

    @router.get('/tools')
    def tools(context=Depends(actor)):
        return {'tools': service.tools.describe(), 'enabled': config.tools_enabled}

    @router.post('/tasks', status_code=202)
    def create(body: TaskRequest, context=Depends(actor)):
        if body.kind == 'chat':
            if body.steps is not None or body.message is None:
                raise HTTPException(400, 'Chat tasks accept a message and optional conversation ID')
            payload = {'message': body.message}
        else:
            if body.message is not None or body.conversation_id is not None or body.steps is None:
                raise HTTPException(400, 'Diagnostic tasks accept only explicit steps')
            payload = {'steps': body.steps}
        return call(service.submit, context, body.kind, payload, body.conversation_id)

    @router.get('/tasks')
    def tasks(context=Depends(actor)):
        return {'tasks': call(service.tasks.list, context)}

    @router.get('/tasks/{task_id}')
    def task(task_id: UUID, context=Depends(actor)):
        return call(service.tasks.get, context, str(task_id)) | {
            'approvals': call(service.approvals.list, context, str(task_id))}

    @router.post('/tasks/{task_id}/cancel')
    def cancel(task_id: UUID, context=Depends(actor)):
        call(service.tasks.cancel, context, str(task_id))
        service._wake.set()
        return call(service.tasks.get, context, str(task_id))

    @router.get('/tasks/{task_id}/events')
    async def events(request: Request, task_id: UUID, after: int = Query(default=0, ge=0), context=Depends(actor)):
        await asyncio.to_thread(call, service.events.read, context, str(task_id), after)
        return StreamingResponse(service.events.stream(context, str(task_id), after, request.is_disconnected),
                                 media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    @router.post('/approvals/{approval_id}')
    def approve(approval_id: UUID, body: ApprovalRequest, context=Depends(actor)):
        call(service.approvals.decide, context, str(approval_id), body.approved)
        service._wake.set()
        return {'saved': True}

    @router.post('/authority/revoke')
    def revoke(context=Depends(actor)):
        call(service.permissions.revoke, context, service.audit)
        return {'revoked': True, 'scope': 'Previously admitted platform tasks; existing account login is preserved'}

    @router.get('/audit/verify')
    def verify(context=Depends(actor)):
        call(service.permissions.require_owner, context)
        return call(service.audit.verify)

    app.include_router(router)
    app.add_middleware(PlatformBodyLimit)
    previous_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application) as state:
            service.start()
            try:
                yield state
            finally:
                await asyncio.to_thread(service.stop)
    app.router.lifespan_context = lifespan
    return service
