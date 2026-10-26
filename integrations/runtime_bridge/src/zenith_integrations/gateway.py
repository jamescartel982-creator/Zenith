"""Account-isolated job gateway; existing Zenith remains the authentication owner."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import re

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from agent.http_security import RequestSecurityMiddleware
from .shared.contracts import JobRequest, GrantRequest
from .shared.identity import ZenithIdentity
from .shared.ledger import Conflict, Ledger
from .shared.router import NativeInference, Router


def public_job(row):
    return {key:row[key] for key in ('id','runtime','operation','status','created','updated','error_code')}


def create_app(config, identity=None, router=None, ledger=None):
    identity = identity or ZenithIdentity(config)
    ledger = ledger or Ledger(config.database, config.secret(config.audit_key_file).encode())
    router = router or Router(NativeInference(config))
    workers = {}
    native_gate = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        ledger.recover()
        try:
            yield
        finally:
            for task in list(workers.values()):
                task.cancel()
            with anyio.CancelScope(shield=True):
                if workers:
                    await asyncio.gather(*list(workers.values()), return_exceptions=True)

    app = FastAPI(title='Zenith integration bridge', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(RequestSecurityMiddleware, allowed_hosts=('127.0.0.1','localhost','::1'))
    app.state.ledger, app.state.router = ledger, router

    @app.middleware('http')
    async def boundary(request, call_next):
        if request.headers.get('origin') or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail':'Browser-origin bridge requests are disabled'},status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse({'detail':'Invalid bridge request'}, status_code=400)

    async def current(request, owner=False):
        return await identity.verify(request.cookies.get('zenith_login',''), owner=owner)

    async def execute(identifier, body, actor, token, adapter):
        try:
            async with native_gate:
                if ledger.stopped():
                    ledger.transition(identifier, {'queued'}, 'cancelled', error='emergency_shutdown')
                    return
                fresh = await identity.verify(token, owner=body.runtime != 'zenith')
                if fresh.id != actor.id or fresh.session_hash != actor.session_hash:
                    raise PermissionError('Identity changed')
                if body.runtime != 'zenith' and not ledger.allows(fresh, body.grant_id,
                        'jobs.submit.'+body.runtime, {'runtime':body.runtime,'operation':body.operation}):
                    raise PermissionError('Grant expired or was revoked')
                if not ledger.transition(identifier, {'queued'}, 'running'):
                    return
                result = await asyncio.wait_for(adapter.execute(body.payload), timeout=config.job_timeout)
                ledger.transition(identifier, {'running'}, 'succeeded', result=result)
        except asyncio.CancelledError:
            ledger.transition(identifier, {'queued','running','cancel_requested'}, 'cancelled', error='operator_cancelled')
            raise
        except Exception:
            # Upstream exceptions and outputs may contain private prompts or keys.
            ledger.transition(identifier, {'queued','running','cancel_requested'}, 'failed', error='runtime_did_not_complete')
        finally:
            workers.pop(identifier, None)

    @app.get('/healthz')
    async def health(request: Request):
        await current(request)
        return {'status':'ok','stopped':ledger.stopped(),'live_execution':False}

    @app.get('/v1/runtimes')
    async def runtimes(request: Request):
        await current(request)
        rows = router.status()
        for row in rows:
            row['configured'] = row.pop('connected')
            row['connected'] = False
        native = router.adapters.get('zenith')
        if native and hasattr(native, 'health') and not ledger.stopped():
            rows[0]['connected'] = await native.health()
        return {'runtimes':rows,'primary_model':'zenith','live_execution':False}

    @app.post('/v1/grants')
    async def grant(request: Request, body: GrantRequest):
        actor = await current(request, owner=True)
        if ledger.stopped():
            raise HTTPException(503,'Emergency shutdown is active')
        return ledger.grant(actor, body.capability, body.scope, body.seconds)

    @app.delete('/v1/grants/{identifier}')
    async def revoke(identifier: str, request: Request):
        actor = await current(request, owner=True)
        if not ledger.revoke(actor, identifier):
            raise HTTPException(404,'Grant not found')
        return {'revoked':True}

    @app.post('/v1/control/stop')
    async def stop(request: Request):
        # Current MFA is required to change control-plane state.
        actor = await current(request, owner=True)
        ledger.shutdown(actor)
        for task in list(workers.values()):
            task.cancel()
        return {'stopped':True,'all_grants_revoked':True}

    @app.post('/v1/control/resume')
    async def resume(request: Request):
        actor = await current(request, owner=True)
        ledger.resume(actor)
        return {'stopped':False,'grants_restored':False}

    @app.post('/v1/jobs', status_code=202)
    async def submit(request: Request, body: JobRequest):
        actor = await current(request, owner=body.runtime != 'zenith')
        if ledger.stopped():
            raise HTTPException(503,'Emergency shutdown is active')
        adapter = router.resolve(body.runtime)
        if body.runtime == 'zenith' and (body.payload.get('model','zenith') != 'zenith' or body.payload.get('stream') is True):
            raise HTTPException(400,'Bridge jobs use complete native Zenith responses')
        if body.runtime != 'zenith' and not ledger.allows(actor, body.grant_id,
                'jobs.submit.'+body.runtime, {'runtime':body.runtime,'operation':body.operation}):
            raise HTTPException(403,'A current capability grant for this exact runtime and operation is required')
        key = request.headers.get('idempotency-key','')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',key):
            raise HTTPException(400,'Provide a stable opaque Idempotency-Key')
        try:
            row, admitted = ledger.admit(actor,key,body.model_dump())
        except Conflict:
            raise HTTPException(409,'Idempotency conflict or work queue limit') from None
        if admitted:
            task = asyncio.create_task(execute(row['id'],body,actor,request.cookies['zenith_login'],adapter))
            workers[row['id']] = task
            def finished(done):
                workers.pop(row['id'], None)
                if done.cancelled():
                    ledger.transition(row['id'], {'queued','running','cancel_requested'}, 'cancelled', error='operator_cancelled')
            task.add_done_callback(finished)
        return public_job(row)

    @app.get('/v1/jobs/{identifier}')
    async def status(identifier: str, request: Request):
        row = ledger.get(identifier, await current(request))
        if row is None:
            raise HTTPException(404,'Job not found')
        return public_job(row)

    @app.get('/v1/jobs/{identifier}/result')
    async def result(identifier: str, request: Request):
        row = ledger.get(identifier, await current(request))
        if row is None:
            raise HTTPException(404,'Job not found')
        if row['status'] != 'succeeded':
            raise HTTPException(409,'A completed result is not available')
        return {'job':public_job(row),'result':json.loads(row['result'])}

    @app.post('/v1/jobs/{identifier}/cancel')
    async def cancel(identifier: str, request: Request):
        actor = await current(request)
        row = ledger.get(identifier,actor)
        if row is None:
            raise HTTPException(404,'Job not found')
        changed = ledger.transition(identifier, {'queued','running'}, 'cancel_requested')
        task = workers.get(identifier)
        if changed and task:
            task.cancel()
        elif changed:
            ledger.transition(identifier, {'cancel_requested'}, 'interrupted', error='native_reconciliation_required')
        return public_job(ledger.get(identifier,actor))
    return app
