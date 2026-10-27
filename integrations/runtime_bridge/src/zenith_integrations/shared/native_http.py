"""Bounded native-runtime HTTP. Mutating calls are never blindly retried."""
import asyncio
import json
import re
import httpx
from ..config import private_origin
from .secrets import read_private
from .redaction import redact


class NativeRefused(RuntimeError):
    pass


class NativeUnavailable(RuntimeError):
    pass


class UnknownExecution(RuntimeError):
    """The native runtime may have accepted work; reconcile instead of replaying."""


class NativeHTTP:
    def __init__(self, origin, key_file, timeout=10, transport=None):
        if isinstance(timeout,bool) or not 0<timeout<=60:
            raise ValueError('Use a bounded native HTTP timeout')
        self.origin=private_origin(origin)
        self.key_file,self.timeout,self.transport=key_file,timeout,transport

    async def request(self, method, path, body=None, headers=None):
        if method not in {'GET','POST'} or not path.startswith('/') or path.startswith('//') or '?' in path or '#' in path:
            raise ValueError('Only fixed native API paths are allowed')
        token=read_private(self.key_file,maximum=1024).strip()
        if not 32<=len(token)<=512 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError('Configure a dedicated strong native profile credential')
        supplied=headers or {}
        if set(supplied)-{'Idempotency-Key','X-Hermes-Session-Key','X-Zenith-Account'}:
            raise ValueError('Untrusted native authentication/routing override')
        try:
            async with httpx.AsyncClient(base_url=self.origin,transport=self.transport,follow_redirects=False,trust_env=False,
                    timeout=self.timeout,headers={'Authorization':'Bearer '+token,**supplied}) as client:
                async with asyncio.timeout(self.timeout):
                    async with client.stream(method,path,json=body) as response:
                        data=bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(data)+len(chunk)>1024*1024:
                                if method=='POST':
                                    raise UnknownExecution('Native response exceeded its budget after submission')
                                raise NativeRefused('native_response_budget_exceeded')
                            data.extend(chunk)
                        if not 200<=response.status_code<300:
                            # Preserve refusal classification, never exception bodies/keys/prompts.
                            if method=='POST' and response.status_code not in {400,401,403,404}:
                                raise UnknownExecution('Native submission/control status requires reconciliation')
                            raise NativeRefused('native_http_'+str(response.status_code))
                        try:
                            value=json.loads(data)
                        except (ValueError,RecursionError):
                            if method=='POST':
                                raise UnknownExecution('Malformed native response after submission') from None
                            raise NativeUnavailable('Malformed native read response') from None
                        if not isinstance(value,dict):
                            if method=='POST':
                                raise UnknownExecution('Invalid native response after submission')
                            raise NativeRefused('invalid_native_response')
                        return redact(value,(token,))
        except (NativeRefused,ValueError):
            raise
        except (httpx.HTTPError,TimeoutError):
            if method=='POST':
                raise UnknownExecution('Native admission/control outcome requires reconciliation') from None
            raise NativeUnavailable('Native status is unavailable') from None


def opaque_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',value):
        raise NativeRefused('invalid_native_identifier')
    return value
