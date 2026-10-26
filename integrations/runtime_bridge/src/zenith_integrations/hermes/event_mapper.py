"""Native terminal states remain distinct from acknowledgements and partial diagnostics."""
from ..shared.native_http import NativeRefused


def terminal_report(value,run_id,session_id):
    if value.get('run_id')!=run_id or value.get('session_id') not in (None,session_id):
        raise NativeRefused('native_event_identity_mismatch')
    state=value.get('status')
    if state not in {'completed','failed','cancelled','interrupted'}:
        raise NativeRefused('native_event_not_terminal')
    return {'runtime':'hermes','native_run_id':run_id,'native_session_id':session_id,
            'status':state,'output':value.get('output') if state=='completed' else None,
            'usage':value.get('usage'),'model_attribution':value.get('runtime')}
