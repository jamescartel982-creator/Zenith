"""Authenticated private native-service jobs. No live-order or broker routes exist."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json

from fastapi import FastAPI,Depends,HTTPException,Request,Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from zenith_integrations.shared.http_boundary import PrivateAPIBoundary
from zenith_integrations.shared.identity import User
from zenith_integrations.shared.ledger import Conflict
from . import PIN
from .contracts import ResearchRequest
from .execution import scoped_account,NativeWorkerFailure


def create_app(executor,auth,ledger):
    tasks={}
    @asynccontextmanager
    async def lifespan(app):
        ledger.recover()
        yield
        for task in list(tasks.values()):task.cancel()
        await asyncio.gather(*list(tasks.values()),return_exceptions=True)
    app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.add_middleware(PrivateAPIBoundary)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        return JSONResponse({'error':'unsupported_or_invalid_research_request'},status_code=422)

    def permission(capability):
        def verify(request:Request):return auth.authenticate(request,capability)
        return verify
    def owner(principal,account):return User(scoped_account(principal.name,account),principal.name)

    @app.get('/healthz')
    async def health(principal=Depends(permission('jobs.read'))):
        try:await asyncio.to_thread(executor.ready)
        except Exception:raise HTTPException(503,'pinned_native_source_unavailable') from None
        return {'runtime':'tradingagents','target_source_pin':PIN,'model':'zenith','stopped':ledger.stopped(),
                'operations':['research','backtest'],'live_orders_enabled':False,'sandbox_attested':False}

    async def perform(identifier,principal,request,user):
        try:
            if ledger.stopped() or not ledger.transition(identifier,{'queued'},'running'):
                ledger.transition(identifier,{'queued'},'cancelled',error='stopped_before_start')
                return
            report=await executor.execute(identifier,principal,request)
            ledger.transition(identifier,{'running'},'succeeded',result=report)
        except asyncio.CancelledError:
            ledger.transition(identifier,{'queued','running','cancel_requested'},'cancelled',error='owned_worker_cancelled')
            raise
        except NativeWorkerFailure as exc:
            ledger.transition(identifier,{'queued','running','cancel_requested'},'failed',error='native_worker_'+exc.code)
        except Exception:
            ledger.transition(identifier,{'queued','running','cancel_requested'},'failed',error='native_research_failed')
        finally:
            tasks.pop(identifier,None)

    @app.post('/v1/jobs',status_code=202)
    async def submit(request:Request,body:ResearchRequest,principal=Depends(permission('jobs.submit'))):
        values=request.headers.getlist('idempotency-key')
        import re
        if len(values)!=1 or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',values[0]):
            raise HTTPException(400,'stable_idempotency_key_required')
        if ledger.stopped():raise HTTPException(503,'native_service_stopped')
        user=owner(principal,body.account_id)
        try:row,admitted=ledger.admit(user,values[0],{'runtime':'tradingagents','operation':body.operation,'payload':body.model_dump()})
        except Conflict:raise HTTPException(409,'native_job_admission_conflict') from None
        if admitted:
            task=asyncio.create_task(perform(row['id'],principal,body,user));tasks[row['id']]=task
            # A cancellation before the coroutine first executes still gets a terminal receipt.
            def complete(done):
                if done.cancelled():ledger.transition(row['id'],{'queued','running','cancel_requested'},'cancelled',error='owned_worker_cancelled')
                tasks.pop(row['id'],None)
            task.add_done_callback(complete)
        return {'id':row['id'],'status':row['status'],'admitted':admitted}

    account_query=Query(min_length=1,max_length=128,pattern=r'^[a-zA-Z0-9_-]+$')
    @app.get('/v1/jobs/{identifier}')
    async def status(identifier:str,account_id:str=account_query,principal=Depends(permission('jobs.read'))):
        row=ledger.get(identifier,owner(principal,account_id))
        if not row:raise HTTPException(404,'job_not_found')
        return {'id':row['id'],'status':row['status'],'error_code':row['error_code'],
                'result':json.loads(row['result']) if row['result'] is not None else None}

    @app.post('/v1/jobs/{identifier}/cancel')
    async def cancel(identifier:str,account_id:str=account_query,principal=Depends(permission('jobs.cancel'))):
        row=ledger.get(identifier,owner(principal,account_id))
        if not row:raise HTTPException(404,'job_not_found')
        task=tasks.get(identifier)
        if task:
            ledger.transition(identifier,{'queued','running'},'cancel_requested');task.cancel()
        return {'id':identifier,'status':ledger.get(identifier,owner(principal,account_id))['status']}

    @app.post('/v1/control/stop')
    async def stop(principal=Depends(permission('grants.manage'))):
        ledger.shutdown(User(principal.name,principal.name))
        for task in list(tasks.values()):task.cancel()
        return {'stopped':True,'termination_pending':bool(tasks)}

    @app.post('/v1/control/resume')
    async def resume(principal=Depends(permission('grants.manage'))):
        ledger.resume(User(principal.name,principal.name))
        return {'stopped':False,'automatic_replay':False}
    return app
