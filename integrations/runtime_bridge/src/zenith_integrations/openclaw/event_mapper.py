"""Do not mistake native admission, partial text or cancellation for completion."""
from ..shared.native_http import NativeRefused
from ..shared.redaction import redact


def chat_event(frame,session_key,run_id,secrets=()):
    if frame.get('type')!='event' or frame.get('event')!='chat':
        return None
    value=frame.get('payload',{})
    if not isinstance(value,dict):
        raise NativeRefused('invalid_native_chat_payload')
    if value.get('sessionKey')!=session_key or value.get('runId')!=run_id:
        return None
    if type(value.get('seq')) is not int or value['seq']<0:
        raise NativeRefused('invalid_native_chat_sequence')
    if value.get('state') not in {'status','delta','final','error','aborted'}:
        raise NativeRefused('unsupported_native_chat_state')
    return redact({'runtime':'openclaw','native_run_id':run_id,'native_session_key':session_key,
                   'sequence':value['seq'],'state':value['state'],
                   'message':value.get('message'),'delta':value.get('deltaText'),
                   'usage':value.get('usage'),
                   'stop_reason':value.get('stopReason'),
                   'local_model_may_still_be_finishing':value.get('localModelMayStillBeFinishing') is True},secrets)
