"""Optional authenticated Cloudflare transport around the unchanged Zenith app."""
import argparse
import hmac
import ipaddress
import os
import re
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from .http_security import security_headers

SECRET = re.compile(r'[A-Za-z0-9_-]{32,256}\Z')


class CloudflareOrigin:
    def __init__(self, app, secret, allowed_hosts):
        if not isinstance(secret, str) or not SECRET.fullmatch(secret):
            raise ValueError('Configure a separate random ZENITH_ORIGIN_SECRET of 32–256 URL-safe characters')
        self.app, self.secret, self.allowed_hosts = app, secret, frozenset(allowed_hosts)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            return await self.app(scope, receive, send)
        if scope['type'] != 'http':
            if scope['type'] == 'websocket': await send({'type':'websocket.close','code':1008})
            return
        headers = {}
        for name, value in scope.get('headers', []): headers.setdefault(name.lower(), []).append(value)
        supplied = headers.get(b'x-zenith-origin-secret', [])
        origins = headers.get(b'x-zenith-public-origin', [])
        clients = headers.get(b'x-zenith-client-ip', [])
        valid = len(supplied) == 1 and hmac.compare_digest(supplied[0], self.secret.encode()) and len(origins) == 1
        try:
            public = urlsplit(origins[0].decode('ascii')) if valid else None
            if (not public or public.scheme != 'https' or not public.hostname or public.hostname not in self.allowed_hosts
                    or public.username or public.password or public.path or public.query or public.fragment
                    or public.netloc != origins[0].decode('ascii')[len('https://'):]
                    or (public.port is not None and not 1 <= public.port <= 65535)):
                valid = False
        except (ValueError, UnicodeError): valid = False
        client = scope.get('client')
        if valid and clients:
            try:
                if len(clients) != 1: raise ValueError('Ambiguous client address')
                client = (str(ipaddress.ip_address(clients[0].decode('ascii'))), 0)
            except (ValueError, UnicodeError): valid = False
        if not valid:
            return await JSONResponse({'detail':'Authenticated Zenith gateway required'}, status_code=403,
                                      headers=security_headers(scope))(scope, receive, send)
        # Only an authenticated gateway may supply these values. Keep the
        # browser Origin unchanged so the original app still enforces CSRF.
        clean = [(name, value) for name, value in scope['headers']
                 if name.lower() not in {b'host', b'forwarded'} and not name.lower().startswith((b'x-zenith-', b'x-forwarded-'))]
        clean.append((b'host', public.netloc.encode('ascii')))
        trusted = {**scope, 'scheme':'https', 'server':(public.hostname, public.port or 443), 'headers':clean, 'client':client}
        return await self.app(trusted, receive, send)


def create_origin(settings=None, agent=None, secret=None, require_checkpoint=False):
    from .config import Settings
    from .server import create_app
    settings = settings or Settings()
    if len(settings.api_token) < 32:
        raise ValueError('Public deployment requires a strong ZENITH_API_TOKEN in addition to the origin secret')
    secret = os.getenv('ZENITH_ORIGIN_SECRET', '') if secret is None else secret
    if secret == settings.api_token:
        raise ValueError('Origin and server access secrets must be different')
    # Validate before opening the app/database or creating any state.
    CloudflareOrigin(None, secret, settings.allowed_hosts)
    if require_checkpoint:
        try:
            if settings.provider != 'huggingface' or not settings.adapter or not settings.checkpoint_receipt:
                raise ValueError('Missing trained checkpoint selection')
            from .deployment import validate_activation
            validate_activation(settings)
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError('Restore and verify the existing trained checkpoint before hosting') from None
    app = create_app(settings, agent)
    from .redaction import Redactor
    app.state.agent.redactor.secrets = Redactor((*app.state.agent.redactor.secrets, secret)).secrets
    return CloudflareOrigin(app, secret, settings.allowed_hosts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '7860')))
    parser.add_argument('--require-checkpoint', action='store_true', help='Refuse missing, changed or unapproved trained state before opening the app')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error('Port must be 1–65535')
    try: app = create_origin(require_checkpoint=args.require_checkpoint)
    except ValueError as exc: parser.error(str(exc))
    import uvicorn
    # Forwarded values are validated by the authenticated wrapper, not by
    # arbitrary X-Forwarded-* headers from the public network.
    uvicorn.run(app, host=args.host, port=args.port, workers=1, proxy_headers=False, access_log=False)


if __name__ == '__main__': main()
