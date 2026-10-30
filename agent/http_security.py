"""HTTP trust boundaries applied before routing or JSON validation."""
import ipaddress
import logging
import re
from urllib.parse import urlsplit

import anyio
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 512 * 1024
BODY_TIMEOUT_SECONDS = 15
LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')


def security_headers(scope):
    headers = {
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    }
    # The ASGI scheme must come from the server/trusted proxy, never an arbitrary
    # request header interpreted here. Do not force HSTS on local HTTP development.
    if scope.get('scheme') == 'https':
        headers['Strict-Transport-Security'] = 'max-age=31536000'
    return headers


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

        response_started = response_finished = False
        original_send = send
        async def protected_send(message):
            nonlocal response_started, response_finished
            if message['type'] == 'http.response.start':
                response_started = True
                protected = [(key.lower().encode('ascii'), value.encode('ascii')) for key, value in security_headers(scope).items()]
                names = {key for key, _ in protected}
                message = {**message, 'headers': [(key, value) for key, value in message.get('headers', []) if key.lower() not in names] + protected}
            elif message['type'] == 'http.response.body' and not message.get('more_body', False):
                response_finished = True
            await original_send(message)
        send = protected_send

        async def reject(status, detail):
            headers = {}
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

        origins = headers.get(b'origin', [])
        if scope.get('method') in {'POST', 'PUT', 'PATCH', 'DELETE'} and origins:
            try:
                if len(origins) != 1:
                    raise ValueError('Ambiguous Origin')
                origin = urlsplit(origins[0].decode('ascii'))
                scheme = scope.get('scheme', 'http')
                expected_port = port or (443 if scheme == 'https' else 80)
                origin_port = origin.port or (443 if origin.scheme == 'https' else 80)
                if (origin.scheme != scheme or not origin.hostname or origin.hostname.lower().rstrip('.') != host.lower()
                        or origin_port != expected_port or origin.username or origin.password or origin.path or origin.query or origin.fragment):
                    raise ValueError('Foreign Origin')
            except (UnicodeError, ValueError):
                return await reject(403, 'Cross-site changes are not allowed')

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

        try:
            return await self.app(scope, bounded_receive, send)
        except Exception:
            # Upstream exceptions may contain API keys, prompts or credentials.
            # Handle before ServerErrorMiddleware can re-raise into access logs.
            logging.getLogger('zenith').error('Request failed; internal exception details withheld')
            if not response_started:
                return await JSONResponse({'detail': 'Request failed. Check the server configuration.'}, status_code=500)(scope, bounded_receive, send)
            if not response_finished:
                try: await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
                except Exception: pass  # The client may already have disconnected.
