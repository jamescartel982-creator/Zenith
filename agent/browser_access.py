"""Short-lived HttpOnly browser grants; the server API key stays server-side."""
import hashlib
import hmac
import re
import secrets
import time

COOKIE = 'zenith_access'
LIFETIME = 3600
FORMAT = re.compile(r'v1\.([0-9]{1,12})\.([A-Za-z0-9_-]{32})\.([a-f0-9]{64})\Z')


def issue(api_token, now=None):
    if not api_token:
        raise ValueError('A configured server credential is required')
    expires = int(time.time() if now is None else now) + LIFETIME
    content = f'v1.{expires}.{secrets.token_urlsafe(24)}'
    signature = hmac.new(api_token.encode(), ('zenith-browser-access\0' + content).encode('ascii'), hashlib.sha256).hexdigest()
    return content + '.' + signature


def valid(cookie, api_token, now=None):
    if not api_token or not isinstance(cookie, str) or len(cookie) > 160:
        return False
    match = FORMAT.fullmatch(cookie)
    if match is None:
        return False
    current = time.time() if now is None else now
    if not current < int(match[1]) <= current + LIFETIME:
        return False
    content, signature = cookie.rsplit('.', 1)
    expected = hmac.new(api_token.encode(), ('zenith-browser-access\0' + content).encode('ascii'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
