"""Pinned public Hermes Runs API; preserves native execution, sessions and risk boundaries."""
import asyncio
from dataclasses import dataclass
import time

from ..shared.native_http import NativeHTTP, NativeRefused, UnknownExecution, opaque_id

PIN='d05095663342556788cf2a198bfa7844cc7968ab'
TERMINAL=frozenset({'completed','failed','cancelled','interrupted'})


@dataclass(frozen=True)
class HermesRun:
    run_id: str
    session_id: str
    idempotency_key: str
    profile_id: str


class HermesAPI:
    def __init__(self, origin, key_file, profile_id, timeout=10, transport=None):
        self.http=NativeHTTP(origin,key_file,timeout,transport)
        self.profile_id=opaque_id(profile_id)
        self.capabilities=None

    async def discover(self):
        data=await self.http.request('GET','/v1/capabilities')
        features=data.get('features',{})
        if not isinstance(features,dict) or not isinstance(data.get('auth'),dict):
            raise NativeRefused('malformed_native_capabilities')
        durable=features.get('runs_idempotency',{})
        if data.get('object')!='hermes.api_server.capabilities' or data.get('platform')!='hermes-agent' or data.get('auth',{}).get('required') is not True:
            raise NativeRefused('unsupported_or_unauthenticated_hermes')
        if not all(features.get(k) is True for k in ('run_submission','run_status','run_stop')) or not isinstance(durable,dict) or durable.get('supported') is not True or durable.get('durable') is not True:
            raise NativeRefused('durable_native_run_controls_required')
        endpoints=data.get('endpoints',{})
        if not isinstance(endpoints,dict):
            raise NativeRefused('malformed_native_endpoints')
        expected={'runs':('POST','/v1/runs'),'run_status':('GET','/v1/runs/{run_id}'),'run_stop':('POST','/v1/runs/{run_id}/stop')}
        for name,(method,path) in expected.items():
            if endpoints.get(name)!={'method':method,'path':path}:
                raise NativeRefused('native_endpoint_contract_mismatch')
        self.capabilities=data
        return {'runtime':'hermes','profile_id':self.profile_id,'agent_alias':data.get('model'),
                'durable_runs':True,'target_source_pin':PIN}

    async def submit(self, text, session_id, idempotency_key):
        if not self.capabilities:
            await self.discover()
        opaque_id(session_id)
        opaque_id(idempotency_key)
        if not isinstance(text,str) or not 1<=len(text)<=16000:
            raise ValueError('Provide a bounded supporting task')
        payload={'input':text,'session_id':session_id,'model':'zenith','provider':'custom'}
        response=await self.http.request('POST','/v1/runs',payload,{'Idempotency-Key':idempotency_key})
        try:
            run_id=opaque_id(response.get('run_id'))
        except NativeRefused:
            raise UnknownExecution('Hermes admission did not return a usable run handle') from None
        if response.get('session_id') not in (None,session_id):
            raise UnknownExecution('Hermes admission session requires reconciliation')
        if response.get('status') not in {'started','queued','running','completed','failed','cancelled','interrupted'}:
            raise UnknownExecution('Hermes admitted an unrecognized native state')
        return HermesRun(run_id,session_id,idempotency_key,self.profile_id)

    def check_handle(self,handle):
        if not isinstance(handle,HermesRun) or handle.profile_id!=self.profile_id:
            raise NativeRefused('native_profile_mismatch')
        opaque_id(handle.run_id)
        opaque_id(handle.session_id)

    async def status(self,handle):
        self.check_handle(handle)
        value=await self.http.request('GET','/v1/runs/'+handle.run_id)
        if value.get('object')!='hermes.run' or value.get('run_id')!=handle.run_id:
            raise NativeRefused('native_run_identity_mismatch')
        if value.get('session_id') not in (None,handle.session_id):
            raise NativeRefused('native_session_mismatch')
        if value.get('status')=='completed':
            runtime=value.get('runtime') or {}
            if not isinstance(runtime,dict) or runtime.get('model')!='zenith' or runtime.get('provider')!='custom':
                raise NativeRefused('actual_zenith_model_attribution_required')
        return value

    async def stop(self,handle):
        self.check_handle(handle)
        return await self.http.request('POST','/v1/runs/'+handle.run_id+'/stop',{})

    async def wait(self,handle,seconds=120):
        if not 0<seconds<=900:
            raise ValueError('Use a bounded native wait')
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=await self.status(handle)
            state=value.get('status')
            if state in TERMINAL:
                return value
            if state=='unknown':
                raise UnknownExecution('Native owner restarted; explicit native reconciliation is required')
            if state not in {'started','running','queued','pending','waiting_for_approval'}:
                raise NativeRefused('unsupported_native_run_state')
            await asyncio.sleep(min(0.2,max(0,deadline-time.monotonic())))
        # Do not label a network wait timeout as a cancelled native run.
        raise UnknownExecution('Native wait expired; the run may still be executing')
