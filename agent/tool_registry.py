"""Adapter to Zenith's registered fixed capabilities; scope remains server-owned."""
from .execution import CAPABILITIES, authorized_addresses


class ToolRegistry:
    def __init__(self, permissions, execution):
        self.permissions, self.execution = permissions, execution

    def describe(self):
        return [{'id': name, 'version': 1, 'description': description,
                 'effect': 'isolated-code' if name == 'sandbox-python' else 'network-read' if name in {'tcp-connect', 'tls-certificate'} else 'offline',
                 'requires_owner_mfa': True, 'requires_explicit_grant': True,
                 'requires_action_approval': name in {'tcp-connect', 'tls-certificate', 'sandbox-python'}}
                for name, description in CAPABILITIES.items()]

    def prepare(self, actor, call):
        scope = self.permissions.require_tool(actor, call.tool)
        if call.tool == 'sandbox-python':
            from .sandbox import SandboxPolicy
            if not SandboxPolicy.from_env().enabled:
                raise PermissionError('Isolated Python execution is disabled')
        if call.tool in {'tcp-connect', 'tls-certificate'}:
            arguments = call.arguments
            authorized_addresses(arguments['host'], arguments['port'], scope)
        return call.tool in {'tcp-connect', 'tls-certificate', 'sandbox-python'}

    def execute(self, actor, call, guard=None):
        self.prepare(actor, call)
        def authority():
            self.permissions.validate(actor)
            if guard is not None:guard()
        return self.execution.execute_session(actor.user_id, actor.session_hash, call.tool, call.arguments, authority)
