"""Integration-owned native session names; foreign native session IDs stay opaque."""
from ..hermes.session_bridge import session_name
from ..shared.native_http import opaque_id


def session_key(account_id,conversation_id,profile_id,key,agent_id='zenith'):
    opaque_id(agent_id)
    return 'agent:'+agent_id+':'+session_name(account_id,conversation_id,profile_id,key)
