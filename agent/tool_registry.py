"""Adapter to Zenith's seven existing capabilities; scope remains server-owned."""
from .execution import CAPABILITIES, authorized_addresses


class ToolRegistry:
    def __init__(self, permissions, execution):
        self.permissions, self.execution = permissions, execution

    def describe(self):
        return [{'id': name, 'version': 1, 'description': description,
                 'effect': 'network-read' if name in {'tcp-connect', 'tls-certificate'} else 'offline',
                 'requires_owner_mfa': True, 'requires_explicit_grant': True,
                 'requires_action_approval': name in {'tcp-connect', 'tls-certificate'}}
                for name, description in CAPABILITIES.items()]

    def prepare(self, actor, call):
        scope = self.permissions.require_tool(actor, call.tool)
        if call.tool in {'tcp-connect', 'tls-certificate'}:
            arguments = call.arguments
            authorized_addresses(arguments['host'], arguments['port'], scope)
        return call.tool in {'tcp-connect', 'tls-certificate'}

    def execute(self, actor, call, guard=None):
        self.prepare(actor, call)
        def authority():
            self.permissions.validate(actor)
            if guard is not None:guard()
        return self.execution.execute_session(actor.user_id, actor.session_hash, call.tool, call.arguments, authority)
