"""Account-isolated job gateway; existing Zenith remains the authentication owner."""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import re
import hashlib
import hmac

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .shared.http_boundary import PrivateAPIBoundary
from .shared.contracts import JobRequest, GrantRequest
from .shared.identity import ZenithIdentity
from .shared.ledger import Conflict, Ledger
from .shared.router import NativeInference, Router
from .shared.native_http import UnknownExecution


def public_job(row):
    return {key:row[key] for key in ('id','runtime','operation','status','created','updated','error_code')}


def create_app(config, identity=None, router=None, ledger=None):
    identity = identity or ZenithIdentity(config)
    ledger = ledger or Ledger(config.database, config.secret(config.audit_key_file).encode())
    router = router or Router(NativeInference(config))
    if config.hermes_origin or config.openclaw_url:
        session_secret = hmac.new(config.secret(config.audit_key_file).encode(), b'zenith-native-sessions-v1', hashlib.sha256).digest()
        if config.hermes_origin:
            from .hermes.api_client import HermesAPI
            from .hermes.adapter import HermesChat
            router.adapters['hermes'] = HermesChat(HermesAPI(config.hermes_origin, config.hermes_key_file, config.hermes_profile_id), config.hermes_profile_id, session_secret, config.job_timeout)
        if config.openclaw_url:
            from .openclaw.gateway_client import GatewayClient
            from .openclaw.adapter import OpenClawChat
            router.adapters['openclaw'] = OpenClawChat(lambda: GatewayClient(config.openclaw_url, config.openclaw_private_key_file, config.openclaw_device_token_file), config.openclaw_profile_id, session_secret, config.job_timeout)
    if config.trading_origin:
        from .tradingagents.client import TradingResearch
        router.adapters['tradingagents']=TradingResearch(config.trading_origin,config.trading_key_file,config.job_timeout)
    workers = {}
    native_gates = {name:asyncio.Lock() for name in ('zenith','hermes','openclaw','tradingagents')}

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
    app.add_middleware(PrivateAPIBoundary)
    app.state.ledger, app.state.router = ledger, router

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse({'detail':'Invalid bridge request'}, status_code=400)

    async def current(request, owner=False):
        return await identity.verify(request.cookies.get('zenith_login',''), owner=owner)

    def required_scope(body):
        scope={'runtime':body.runtime,'operation':body.operation}
        if body.runtime in {'hermes','openclaw'}:
            from .shared.native_task import chat_scope
            try:
                scope.update(chat_scope(body.payload, body.operation))
            except RuntimeError:
                raise HTTPException(400, 'Only an explicit bounded message and conversation are enabled') from None
        if body.runtime=='tradingagents':
            if body.operation!='research' or set(body.payload)!={'ticker','as_of'} or not all(isinstance(v,str) for v in body.payload.values()):
                raise HTTPException(400,'Only explicit read-only ticker/as_of research is enabled')
            scope.update(body.payload)
        return scope

    def receipt(identifier,actor):
        row=ledger.get(identifier,actor)
        return json.loads(row['result']) if row and row['result'] else None

    async def execute(identifier, body, actor, token, adapter):
        try:
            async with native_gates[body.runtime]:
                if ledger.stopped():
                    ledger.transition(identifier, {'queued'}, 'cancelled', error='emergency_shutdown')
                    return
                fresh = await identity.verify(token, owner=body.runtime != 'zenith')
                if fresh.id != actor.id or fresh.session_hash != actor.session_hash:
                    raise PermissionError('Identity changed')
                if body.runtime != 'zenith' and not ledger.allows(fresh, body.grant_id,
                        'jobs.submit.'+body.runtime, required_scope(body)):
                    raise PermissionError('Grant expired or was revoked')
                if not ledger.transition(identifier, {'queued'}, 'running'):
                    return
                if body.runtime!='zenith':
                    def admitted(native_id,native_state=None):
                        data={'runtime':body.runtime,'native_job_id':native_id}
                        if native_state:data['native_status']=native_state
                        row=ledger.get(identifier,actor)
                        if row and row['status'] in {'running','cancel_requested'}:
                            ledger.transition(identifier,{row['status']},row['status'],result=data)
                    async def authorized():
                        while True:
                            await asyncio.sleep(1)
                            fresh=await identity.verify(token,owner=True)
                            if fresh!=actor or ledger.stopped() or not ledger.allows(fresh,body.grant_id,'jobs.submit.'+body.runtime,required_scope(body)):
                                raise PermissionError('Native execution lease is no longer valid')
                    work=asyncio.create_task(adapter.execute_scoped(body.payload,actor.id,identifier,body.operation,admitted))
                    lease=asyncio.create_task(authorized())
                    try:
                        completed,_=await asyncio.wait((work,lease),timeout=config.job_timeout,return_when=asyncio.FIRST_COMPLETED)
                        if lease in completed or work not in completed:
                            raise PermissionError('Native execution lease expired or deadline elapsed')
                        result=work.result()
                    finally:
                        lease.cancel()
                        if not work.done():work.cancel()
                        with anyio.CancelScope(shield=True):
                            await asyncio.gather(lease,return_exceptions=True)
                            outcome=(await asyncio.gather(work,return_exceptions=True))[0]
                        if isinstance(outcome,UnknownExecution):raise outcome
                else:
                    result = await asyncio.wait_for(adapter.execute(body.payload), timeout=config.job_timeout)
                ledger.transition(identifier, {'running'}, 'succeeded', result=result)
        except UnknownExecution:
            ledger.transition(identifier,{'queued','running','cancel_requested'},'interrupted',result=receipt(identifier,actor),error='native_reconciliation_required')
        except asyncio.CancelledError:
            ledger.transition(identifier, {'queued','running','cancel_requested'}, 'cancelled', result=receipt(identifier,actor),error='operator_cancelled')
            raise
        except Exception:
            # Upstream exceptions and outputs may contain private prompts or keys.
            ledger.transition(identifier, {'queued','running','cancel_requested'}, 'failed',result=receipt(identifier,actor), error='runtime_did_not_complete')
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
        if not ledger.stopped():
            for row in rows:
                adapter=router.adapters.get(row['runtime'])
                if adapter and hasattr(adapter,'health'):row['connected']=await adapter.health()
                if row['runtime']=='tradingagents':row['financial_review_required']=True
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
                'jobs.submit.'+body.runtime, required_scope(body)):
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
        result=public_job(row)
        if row['status'] in {'failed','cancelled','interrupted'} and row['result']:
            data=json.loads(row['result'])
            if data.get('native_job_id'):result['native_receipt']=data
        return result

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
