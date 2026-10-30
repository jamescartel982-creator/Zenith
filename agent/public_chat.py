"""Opt-in guest chat identities; never server-access or administrator grants."""
import hashlib
import hmac
import re
import secrets
import time
from threading import Lock

COOKIE = 'zenith_guest'
LIFETIME = 7 * 86400
FORMAT = re.compile(r'g1\.([0-9]{1,12})\.([A-Za-z0-9_-]{32})\.([a-f0-9]{64})\Z')


def issue(key, now=None):
    expires = int(time.time() if now is None else now) + LIFETIME
    content = f'g1.{expires}.{secrets.token_urlsafe(24)}'
    signature = hmac.new(key.encode(), ('zenith-public-guest\0' + content).encode(), hashlib.sha256).hexdigest()
    return content + '.' + signature


def identity(cookie, key, now=None):
    if not isinstance(cookie, str) or len(cookie) > 160 or not key:
        return None
    match = FORMAT.fullmatch(cookie)
    current = time.time() if now is None else now
    if not match or not current < int(match[1]) <= current + LIFETIME:
        return None
    content, signature = cookie.rsplit('.', 1)
    expected = hmac.new(key.encode(), ('zenith-public-guest\0' + content).encode(), hashlib.sha256).hexdigest()
    return 'guest:' + match[2] if hmac.compare_digest(signature, expected) else None


def set_cookie(response, request, key):
    response.set_cookie(COOKIE, issue(key), max_age=LIFETIME, httponly=True,
                        secure=request.url.scheme == 'https', samesite='strict', path='/')


def guest_route(method, path):
    if method == 'GET' and path in {'/api/account', '/api/team', '/api/knowledge',
                                   '/api/model-packs', '/api/skills', '/api/skills/current'}:
        return True
    if method == 'POST' and path in {'/api/chat', '/api/chat/stream', '/api/skills/command'}:
        return True
    return method in {'GET', 'DELETE'} and re.fullmatch(r'/api/history/[a-fA-F0-9-]{36}', path) is not None


class ChatLimiter:
    """Bounded, single-process per-client admission for the local model service."""
    def __init__(self):
        self.entries = {}
        self.lock = Lock()

    def admit(self, client, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            self.entries = {key: value for key, value in self.entries.items() if now - value[0] < 60}
            started, count = self.entries.get(client, (now, 0))
            if count >= 20 or (client not in self.entries and len(self.entries) >= 1024):
                return False
            self.entries[client] = (started, count + 1)
            return True
