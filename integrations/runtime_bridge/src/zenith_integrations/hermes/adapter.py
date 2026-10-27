"""Account-scoped native Hermes Runs adapter; no shell or model override inputs."""
from .api_client import HermesAPI
from .session_bridge import session_name
from ..shared.native_http import NativeRefused, UnknownExecution, opaque_id
from ..shared.native_task import chat_scope, finish_cleanup


class HermesChat:
    def __init__(self, api, profile_id, session_key, timeout=120, context_probe=None):
        self.api, self.profile_id, self.session_key, self.timeout = api, profile_id, session_key, timeout
        self.context_probe = context_probe
        self.unavailable_reason = None

    async def health(self):
        try:
            self.unavailable_reason = None
            limits = await self.context_probe() if self.context_probe else None
            if not isinstance(limits, dict) or type(limits.get('context_tokens')) is not int or type(limits.get('architectural_context_tokens')) is not int:
                self.unavailable_reason = 'model_context_not_verified'
                return False
            # Audited Hermes custom-provider floor, agent/agent_init.py. Never
            # inflate the advertised window or substitute a larger foundation.
            if min(limits['context_tokens'], limits['architectural_context_tokens']) < 64000:
                self.unavailable_reason = 'native_context_window_below_64000'
                return False
            await self.api.discover()
            tools = await self.api.http.request('GET', '/v1/toolsets')
            # The initial bridge enables conversation only, never native execution tools.
            rows = tools.get('data')
            return tools.get('object') == 'list' and tools.get('platform') == 'api_server' and isinstance(rows, list) and all(isinstance(row, dict) and row.get('enabled') is False for row in rows)
        except Exception:
            return False

    async def execute_scoped(self, payload, account_id, job_id, operation, on_admitted):
        chat_scope(payload, operation)
        opaque_id(account_id); opaque_id(job_id)
        if not await self.health():
            raise NativeRefused('authenticated_tool_free_hermes_required')
        session = session_name(account_id, payload['conversation_id'], self.profile_id, self.session_key)
        handle = await self.api.submit(payload['message'], session, job_id)
        terminal = False
        async def stop():
            await self.api.stop(handle)
            state = await self.api.wait(handle, seconds=10)
            if state.get('status') not in {'completed', 'failed', 'cancelled'}:
                raise UnknownExecution('Hermes termination requires reconciliation')
            on_admitted(handle.run_id, state['status'])
        try:
            on_admitted(handle.run_id)
            result = await self.api.wait(handle, seconds=self.timeout)
            terminal = result.get('status') in {'completed', 'failed', 'cancelled'}
            on_admitted(handle.run_id, result.get('status'))
            if not terminal:
                raise UnknownExecution('Hermes restart requires reconciliation')
            if result['status'] != 'completed':
                raise NativeRefused('native_hermes_did_not_complete')
            return {'runtime': 'hermes', 'native_job_id': handle.run_id, 'result': result}
        except BaseException:
            if not terminal:
                await finish_cleanup(stop())
            raise
