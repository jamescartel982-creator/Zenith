"""HTTP trust boundaries applied before routing or JSON validation."""
import ipaddress
import re
from urllib.parse import urlsplit

import anyio
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 512 * 1024
BODY_TIMEOUT_SECONDS = 15
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')


def validate_hosts(hosts):
    if not isinstance(hosts, tuple) or not hosts:
        raise ValueError('ZENITH_ALLOWED_HOSTS must list explicit host names or IP addresses')
    for host in hosts:
        if not isinstance(host, str) or not host or host != host.lower() or len(host) > 253:
            raise ValueError('Invalid allowed host')
        try:
            ipaddress.ip_address(host)
            continue
        except ValueError:
            pass
        if not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in host.split('.')):
            raise ValueError('Use explicit allowed host names without schemes, ports, or wildcards')


class RequestSecurityMiddleware:
    def __init__(self, app, allowed_hosts, max_body_bytes=MAX_REQUEST_BYTES,
                 body_timeout=BODY_TIMEOUT_SECONDS):
        self.app = app
        self.allowed_hosts = frozenset(allowed_hosts)
        self.max_body_bytes = max_body_bytes
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def reject(status, detail):
            headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
            if scope.get('http_version', '1.1').startswith('1'):
                headers['Connection'] = 'close'
            await JSONResponse({'detail': detail}, status_code=status, headers=headers)(scope, receive, send)

        headers = {}
        for name, value in scope.get('headers', []):
            headers.setdefault(name.lower(), []).append(value)
        hosts = headers.get(b'host', [])
        if len(hosts) != 1:
            return await reject(400, 'Exactly one Host header is required')
        try:
            raw = hosts[0].decode('ascii')
            if not re.fullmatch(r'(?:\[[0-9a-fA-F:.]+\]|[a-zA-Z0-9.-]+)(?::[0-9]{1,5})?', raw):
                raise ValueError('Invalid Host')
            parsed = urlsplit('//' + raw)
            host = parsed.hostname
            port = parsed.port
            if not host or (port is not None and not 1 <= port <= 65535):
                raise ValueError('Invalid Host')
            if host.endswith('.'):
                host = host[:-1]
        except (UnicodeError, ValueError):
            return await reject(400, 'Invalid Host header')
        if host.lower() not in self.allowed_hosts:
            return await reject(400, 'Host is not allowed')

        # Native/API clients may omit browser metadata. A browser explicitly
        # reporting a cross-site API request is rejected even without Origin.
        if scope.get('path', '').startswith('/api/') and any(
                value.lower() == b'cross-site' for value in headers.get(b'sec-fetch-site', [])):
            return await reject(403, 'Cross-site API requests are not allowed')
        lengths = headers.get(b'content-length', [])
        if len(lengths) > 1 or (lengths and b'transfer-encoding' in headers):
            return await reject(400, 'Ambiguous request length')
        if lengths:
            if not re.fullmatch(rb'[0-9]{1,12}', lengths[0]):
                return await reject(400, 'Invalid request length')
            if int(lengths[0]) > self.max_body_bytes:
                return await reject(413, 'Request body is too large')

        body = bytearray()
        try:
            with anyio.fail_after(self.body_timeout):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    if len(body) + len(chunk) > self.max_body_bytes:
                        return await reject(413, 'Request body is too large')
                    body.extend(chunk)
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            return await reject(408, 'Request body timed out')
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        return await self.app(scope, bounded_receive, send)
