"""Selected native Gateway chat backend; device permissions stay outside prompts."""
import asyncio
from .session_bridge import session_key
from ..shared.native_http import NativeRefused, UnknownExecution, opaque_id
from ..shared.native_task import chat_scope, finish_cleanup


def message_text(message):
    if not isinstance(message, dict):return None
    content=message.get('content')
    if isinstance(content,list):
        parts=[p.get('text') for p in content if isinstance(p,dict) and p.get('type')=='text']
        if any(not isinstance(part,str) for part in parts):return None
        content='\n'.join(parts)
    return content if isinstance(content,str) else None


def quality_flags(message):
    content=message_text(message)
    if not isinstance(content,str) or not content.strip():return ['native_answer_not_verified']
    if content.strip().lower() in {'none in the latest retained-input page','unavailable; retained input could not be inspected'}:
        return ['native_context_echo']
    return []


class OpenClawChat:
    def __init__(self, client_factory, profile_id, session_secret, timeout=120):
        self.client_factory, self.profile_id = client_factory, profile_id
        self.session_secret, self.timeout = session_secret, timeout

    async def health(self):
        try:
            async with self.client_factory() as client:
                value = await client.health()
                return isinstance(value, dict) and value.get('ok') is True
        except Exception:
            return False

    async def execute_scoped(self, payload, account_id, job_id, operation, on_admitted):
        chat_scope(payload, operation)
        opaque_id(account_id); opaque_id(job_id)
        session = session_key(account_id, payload['conversation_id'], self.profile_id, self.session_secret)
        async with self.client_factory() as client:
            try:
                admitted = await client.submit_turn(session, payload['message'], job_id)
            except asyncio.CancelledError:
                # The request may already have been accepted. Never acknowledge a
                # confirmed cancellation or replay the bridge job without reconciliation.
                raise UnknownExecution('Native admission was interrupted; reconcile the original job key') from None
            if not isinstance(admitted, dict):
                raise UnknownExecution('Gateway admission requires reconciliation')
            run_id = admitted.get('runId')
            try:
                opaque_id(run_id)
            except NativeRefused:
                raise UnknownExecution('Gateway returned no usable run handle') from None
            terminal = False
            async def stop():
                # Independent connection: never race two readers on the turn socket.
                async with self.client_factory() as control:
                    await control.cancel_turn(session, run_id)
                result = await client.terminal(session, run_id, seconds=10)
                if result.get('local_model_may_still_be_finishing'):
                    raise UnknownExecution('Native model termination is not confirmed')
                on_admitted(run_id, result['state'])
            try:
                on_admitted(run_id)
                result = await client.terminal(session, run_id, seconds=self.timeout)
                terminal = not result.get('local_model_may_still_be_finishing')
                on_admitted(run_id, result['state'])
                if not terminal:
                    raise UnknownExecution('Native model may still be finishing')
                if result['state'] != 'final':
                    raise NativeRefused('native_openclaw_did_not_complete')
                # Model attribution is not invented from the requested model alias.
                flags=quality_flags(result.get('message'))
                return {'runtime': 'openclaw', 'native_job_id': run_id, 'result': result,
                    'quality_flags':flags,'answer_verified':False,'response_review_required':bool(flags)}
            except BaseException:
                if not terminal:
                    await finish_cleanup(stop())
                raise
