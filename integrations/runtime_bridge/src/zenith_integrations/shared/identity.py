"""Read-only current Zenith account/MFA verification at one configured origin."""
from dataclasses import dataclass
import hashlib
import httpx
from fastapi import HTTPException


@dataclass(frozen=True)
class User:
    id: str
    session_hash: str


class ZenithIdentity:
    def __init__(self, config, transport=None):
        self.config, self.transport = config, transport

    async def verify(self, token, owner=False):
        if not isinstance(token, str) or not 16 <= len(token) <= 512 or not token.isascii() or any(c.isspace() for c in token):
            raise HTTPException(401, 'Sign in through the existing Zenith account interface')
        headers = {}
        gate = self.config.secret(self.config.zenith_access_token_file)
        if gate:
            headers['Authorization'] = 'Bearer ' + gate
        try:
            async with httpx.AsyncClient(base_url=self.config.zenith_origin, transport=self.transport,
                                         follow_redirects=False, timeout=5, headers=headers,
                                         cookies={'zenith_login': token}) as client:
                response = await client.get('/api/account')
                if response.status_code != 200:
                    raise HTTPException(401, 'Current Zenith login could not be verified')
                user = response.json().get('user')
                if not isinstance(user, dict) or not isinstance(user.get('id'), str) or not user['id']:
                    raise HTTPException(401, 'Current Zenith login could not be verified')
                if owner:
                    status = await client.get('/api/admin/status')
                    state = status.json() if status.status_code == 200 else {}
                    if not all(state.get(key) is True for key in ('eligible', 'elevated', 'mfa_configured', 'mfa_verified')):
                        raise HTTPException(403, 'Current owner login, elevation and verified MFA are required')
                return User(user['id'], hashlib.sha256(token.encode()).hexdigest())
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError, TypeError):
            raise HTTPException(503, 'Zenith account verification is unavailable') from None
