"""Authenticated native research handoff with fixed account and execution ownership."""
import asyncio
import time
from ..shared.native_http import NativeHTTP,NativeRefused,UnknownExecution,opaque_id

PIN='e8f5503e9b86d5c2710b0c76b1f686703968c9df'


class TradingResearch:
    def __init__(self,origin,key_file,timeout=600,transport=None):
        if not 1<=timeout<=900:raise ValueError('Use a bounded native research deadline')
        self.http=NativeHTTP(origin,key_file,timeout=10,transport=transport)
        self.timeout=timeout

    async def health(self):
        try:
            value=await self.http.request('GET','/healthz')
            return value.get('runtime')=='tradingagents' and value.get('model')=='zenith' and value.get('target_source_pin')==PIN and value.get('stopped') is False and value.get('live_orders_enabled') is False
        except Exception:return False

    async def execute_scoped(self,payload,account_id,job_id,operation,on_admitted):
        if operation!='research' or not isinstance(payload,dict) or set(payload)!={'ticker','as_of'}:
            raise NativeRefused('only_explicit_read_only_research_is_enabled')
        opaque_id(account_id);opaque_id(job_id)
        body={'account_id':account_id,'operation':'research','tickers':[payload['ticker']],'dates':[payload['as_of']]}
        if not await self.health():raise NativeRefused('pinned_native_research_not_ready')
        # Never read account/credential/provider/destination overrides from model text.
        admitted=await self.http.request('POST','/v1/jobs',body,{'Idempotency-Key':job_id})
        try:identifier=opaque_id(admitted.get('id'))
        except NativeRefused:raise UnknownExecution('Native research admission needs reconciliation') from None
        async def status():
            # This path uses a controlled opaque account query, not arbitrary URLs.
            return await self.http.request('GET','/v1/jobs/'+identifier,headers={'X-Zenith-Account':account_id})
        async def cancel_owned():
            await self.http.request('POST','/v1/jobs/'+identifier+'/cancel',{},headers={'X-Zenith-Account':account_id})
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                state=await status()
                if state.get('id')!=identifier:raise UnknownExecution('Native cancellation identity mismatch')
                if state.get('status')=='interrupted':raise UnknownExecution('Native restart requires worker reconciliation')
                if state.get('status') in {'succeeded','failed','cancelled'}:
                    on_admitted(identifier,state['status']);return
                await asyncio.sleep(0.1)
            raise UnknownExecution('Native research termination was not confirmed')
        terminal=False
        try:
            on_admitted(identifier)
            async with asyncio.timeout(self.timeout):
                while True:
                    value=await status()
                    if value.get('id')!=identifier:raise UnknownExecution('Native research identity changed')
                    if value.get('status')=='succeeded':
                        terminal=True
                        report=value.get('result')
                        if not isinstance(report,dict) or report.get('model')!='zenith' or report.get('live_orders_enabled') is not False:
                            raise NativeRefused('invalid_native_research_report')
                        return {'runtime':'tradingagents','native_job_id':identifier,'report':report,'financial_review_required':True}
                    if value.get('status') in {'failed','cancelled','interrupted'}:
                        terminal=True
                        on_admitted(identifier,value['status'])
                        raise NativeRefused('native_research_did_not_complete')
                    if value.get('status') not in {'queued','running','cancel_requested'}:
                        raise UnknownExecution('Unknown native research state')
                    await asyncio.sleep(0.2)
        except BaseException:
            if terminal:raise
            cleanup=asyncio.create_task(cancel_owned())
            while not cleanup.done():
                try:await asyncio.shield(cleanup)
                except asyncio.CancelledError:continue
            cleanup.result()
            raise
