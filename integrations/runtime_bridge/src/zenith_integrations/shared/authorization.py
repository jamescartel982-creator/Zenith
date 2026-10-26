"""Service identity and capability checks; no prompt can mint a grant."""
from dataclasses import dataclass
import hashlib
import hmac
import os
import re

from fastapi import HTTPException
from .secrets import read_json, read_private

CAPABILITIES = frozenset({'inference.read', 'inference.generate', 'jobs.read', 'jobs.submit',
                          'jobs.cancel', 'grants.manage', 'reports.read', 'reports.deliver'})


@dataclass(frozen=True)
class Principal:
    name: str
    capabilities: frozenset[str]
    models: frozenset[str]


class ServiceAuth:
    """Only operator-configured identities exist; credentials grant no native admin role."""
    def __init__(self, records):
        self.records = []
        seen = set()
        if not isinstance(records, list) or not 1 <= len(records) <= 64:
            raise ValueError('Configure 1–64 separate service identities')
        for row in records:
            if not isinstance(row, dict) or set(row) - {'id', 'token_env', 'token_file', 'capabilities', 'models'}:
                raise ValueError('Invalid service identity configuration')
            name = row.get('id', '')
            caps, models = row.get('capabilities', []), row.get('models', [])
            if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', name) or name in seen:
                raise ValueError('Invalid or duplicate service identity')
            if not isinstance(caps, list) or not caps or any(not isinstance(c, str) or c not in CAPABILITIES for c in caps):
                raise ValueError('Unknown service capability')
            if not isinstance(models, list) or any(not isinstance(m, str) or not re.fullmatch(r'[a-z0-9_-]{1,64}', m) for m in models):
                raise ValueError('Invalid model allowlist')
            if bool(row.get('token_env')) == bool(row.get('token_file')):
                raise ValueError('Use exactly one dedicated secret handle')
            if row.get('token_env'):
                key = row['token_env']
                if not isinstance(key, str) or not re.fullmatch(r'ZENITH_(?:INFERENCE|BRIDGE)_[A-Z0-9_]+', key) or key.endswith(('ADMIN_CODE', 'API_TOKEN')):
                    raise ValueError('Use a dedicated integration credential, not the owner secret')
                token = os.environ.get(key, '')
            else:
                token = read_private(row['token_file'], maximum=1024).strip()
            if not 32 <= len(token) <= 512 or not token.isascii() or any(c.isspace() for c in token):
                raise ValueError('Service credentials require at least 32 non-whitespace ASCII characters')
            digest = hashlib.sha256(token.encode()).digest()
            if digest in seen:
                raise ValueError('Different service identities must not share credentials')
            self.records.append((digest, Principal(name, frozenset(caps), frozenset(models))))
            seen.update((name, digest))

    @classmethod
    def from_file(cls, path):
        config = read_json(path)
        if not isinstance(config, dict) or set(config) != {'services'}:
            raise ValueError('Invalid service credential manifest')
        return cls(config['services'])

    def authenticate(self, request, capability, model=None):
        values = request.headers.getlist('authorization')
        if len(values) != 1 or not values[0].startswith('Bearer ') or len(values[0]) > 520:
            raise HTTPException(401, 'Service authentication required', headers={'WWW-Authenticate': 'Bearer'})
        supplied = hashlib.sha256(values[0][7:].encode()).digest()
        matched = None
        for expected, identity in self.records:
            if hmac.compare_digest(expected, supplied):
                matched = identity
        if matched is None:
            raise HTTPException(401, 'Service authentication required', headers={'WWW-Authenticate': 'Bearer'})
        if capability not in matched.capabilities or (model is not None and model not in matched.models):
            raise HTTPException(403, 'Service capability denied')
        return matched
