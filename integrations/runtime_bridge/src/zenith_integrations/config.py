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
    trading_origin: str = ""
    trading_key_file: str = ""
    hermes_origin: str = ""
    hermes_key_file: str = ""
    hermes_profile_id: str = "zenith-hermes"
    openclaw_url: str = ""
    openclaw_private_key_file: str = ""
    openclaw_device_token_file: str = ""
    openclaw_profile_id: str = "zenith-openclaw"

    def __post_init__(self):
        private_origin(self.zenith_origin)
        private_origin(self.inference_origin)
        if bool(self.trading_origin)!=bool(self.trading_key_file):
            raise ValueError('Configure both the dedicated native research origin and key handle')
        if self.trading_origin:private_origin(self.trading_origin)
        if bool(self.hermes_origin) != bool(self.hermes_key_file):
            raise ValueError('Configure both Hermes origin and dedicated key handle')
        if self.hermes_origin:private_origin(self.hermes_origin)
        if any((self.openclaw_url, self.openclaw_private_key_file, self.openclaw_device_token_file)) and not all((self.openclaw_url, self.openclaw_private_key_file, self.openclaw_device_token_file)):
            raise ValueError('Configure the Gateway and both already-paired device key handles')
        if self.openclaw_url:
            parts = urlsplit(self.openclaw_url)
            if parts.scheme not in {'ws','wss'}:
                raise ValueError('A private WebSocket Gateway is required')
            private_origin(('https' if parts.scheme == 'wss' else 'http') + self.openclaw_url[len(parts.scheme):])
        if self.hermes_origin or self.openclaw_url:
            if not self.audit_key_file:
                raise ValueError('Private audit and session binding key required')
            from .shared.native_http import opaque_id
            opaque_id(self.hermes_profile_id); opaque_id(self.openclaw_profile_id)
        if not 1 <= self.job_timeout <= 900:
            raise ValueError('Job timeout must be 1–900 seconds')

    def secret(self, path):
        return read_private(path, maximum=1024).strip() if path else ''
