"""Fixed operator endpoints; requests cannot supply network destinations or secrets."""
from dataclasses import dataclass
from urllib.parse import urlsplit
from .shared.secrets import read_private


def private_origin(value):
    parts = urlsplit(value)
    if parts.scheme not in {'http', 'https'} or parts.hostname not in {'127.0.0.1', 'localhost', '::1'} or parts.username or parts.password or parts.query or parts.fragment or parts.path not in {'', '/'}:
        raise ValueError('Use a fixed loopback origin; remote trust configuration is not enabled')
    return value.rstrip('/')


@dataclass(frozen=True)
class BridgeConfig:
    zenith_origin: str
    inference_origin: str
    inference_key_file: str
    database: str
    zenith_access_token_file: str = ''
    audit_key_file: str = ''
    job_timeout: float = 120

    def __post_init__(self):
        private_origin(self.zenith_origin)
        private_origin(self.inference_origin)
        if not 1 <= self.job_timeout <= 900:
            raise ValueError('Job timeout must be 1–900 seconds')

    def secret(self, path):
        return read_private(path, maximum=1024).strip() if path else ''
