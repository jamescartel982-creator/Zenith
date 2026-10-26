"""Boundary redaction for known service secrets and sensitive structured fields."""
SENSITIVE=frozenset({'authorization','api_key','access_token','refresh_token','device_token','devicetoken',
                     'private_key','privatekey','password','secret'})


def redact(value,secrets=(),depth=0):
    if depth>32:
        return '[REDACTED: depth limit]'
    if isinstance(value,str):
        for secret in secrets:
            if isinstance(secret,str) and len(secret)>=8:
                value=value.replace(secret,'[REDACTED]')
        return value
    if isinstance(value,list):
        return [redact(v,secrets,depth+1) for v in value]
    if isinstance(value,dict):
        return {k:('[REDACTED]' if str(k).lower() in SENSITIVE else redact(v,secrets,depth+1)) for k,v in value.items()}
    return value
