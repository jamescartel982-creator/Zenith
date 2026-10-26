"""Opaque integration-owned session names; never reuse a foreign native UI transcript."""
import hashlib
import hmac
import json


def session_name(account_id,conversation_id,profile_id,key):
    if not all(isinstance(v,str) and v and len(v)<=128 for v in (account_id,conversation_id,profile_id)) or len(key)<32:
        raise ValueError('A scoped account/conversation/profile binding is required')
    raw=json.dumps([account_id,conversation_id,profile_id],ensure_ascii=False,separators=(',',':')).encode()
    return 'zenith_'+hmac.new(key,raw,hashlib.sha256).hexdigest()
