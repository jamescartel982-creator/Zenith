"""Best-effort secret redaction; execution authorization never depends on this."""
import re
import os

REDACTED = '[REDACTED]'
PATTERNS = (
    re.compile(r'zenith-admin-[A-Za-z0-9_-]{43}'),
    re.compile(r'\b(?:sk-(?:ant-)?|hf_)[A-Za-z0-9_-]{16,}'),
    re.compile(r'\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}'),
    re.compile(r'(?i)\bhttps?://[^\s/@:]+:[^\s/@]+@'),
    re.compile(r'(?i)\b(?:password|api[_-]?key|secret|access[_-]?token)\s*[=:]\s*[\'"]?(?!<|\[REDACTED\]|os\.|process\.|settings\.|config\.|getenv\b|environ\b)[^\s\'"]{8,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END [^-]+-----|$)'),
)


class Redactor:
    def __init__(self, secrets=()):
        self.secrets = tuple(sorted({s for s in secrets if isinstance(s, str) and len(s) >= 8}, key=len, reverse=True))

    @classmethod
    def configured(cls, api_token=''):
        return cls([api_token] + [os.getenv(name, '') for name in (
            'ZENITH_API_TOKEN', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
            'HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'GITHUB_TOKEN', 'GH_TOKEN',
            'AZURE_OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY',
            'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')])

    def value(self, value):
        if isinstance(value, str): return self.text(value)
        if isinstance(value, list): return [self.value(item) for item in value]
        if isinstance(value, tuple): return [self.value(item) for item in value]
        if isinstance(value, dict):
            return {self.text(str(key)): REDACTED if isinstance(item, str) and re.fullmatch(
                r'(?i)(?:password|api[_-]?key|secret|access[_-]?token)', str(key)) else self.value(item)
                for key, item in value.items()}
        return value

    def text(self, value):
        if not isinstance(value, str):
            raise ValueError('Redaction expects text')
        for secret in self.secrets:
            value = value.replace(secret, REDACTED)
        for pattern in PATTERNS:
            value = pattern.sub(REDACTED, value)
        return value

    def require_clean(self, value):
        if self.text(value) != value:
            raise ValueError('Remove credentials before submitting persistent input')
        return value


class RedactingStream:
    """Retain possible secret boundaries before releasing provider text.

    Recognized open credential tokens/PEM blocks stay buffered until closed.
    An oversized ambiguous tail fails closed instead of leaking partial content.
    This is best-effort pattern/literal filtering, not a claim to detect every
    possible secret or obfuscated encoding.
    """
    MAX_PENDING = 16384
    MARKERS = ('sk-', 'hf_', 'ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_', 'github_pat_', 'zenith-admin-', 'Bearer ', 'password', 'api_key',
               'api-key', 'apikey', 'secret', 'access_token', 'access-token',
               '-----BEGIN ', 'http://', 'https://')
    OPEN = (
        re.compile(r'\b(?:sk-|hf_|zenith-admin-)[A-Za-z0-9_-]*\Z'),
        re.compile(r'\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]*\Z'),
        re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]*\Z'),
        re.compile(r'(?i)\b(?:password|api[_-]?key|secret|access[_-]?token)\s*(?:[=:]\s*[\'"]?[^\s\'"]*)?\Z'),
        re.compile(r'(?i)\bhttps?://[^\s]*\Z'),
        re.compile(r'-----BEGIN [A-Z -]*\Z'),
    )
    PEM = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')

    def __init__(self, redactor):
        self.redactor, self.pending = redactor, ''

    def feed(self, chunk):
        self.pending += chunk
        cut = len(self.pending)
        lower = self.pending.casefold()
        for marker in self.MARKERS:
            for length in range(1, len(marker)):
                if lower.endswith(marker[:length].casefold()): cut = min(cut, len(self.pending) - length)
        for pattern in self.OPEN:
            match = pattern.search(self.pending)
            if match: cut = min(cut, match.start())
        for match in self.PEM.finditer(self.pending):
            if not re.search(r'-----END [^-]+-----', self.pending[match.end():]):
                cut = min(cut, match.start())
        for secret in self.redactor.secrets:
            for length in range(1, min(8, len(secret))):
                if self.pending.endswith(secret[:length]): cut = min(cut, len(self.pending) - length)
            start = self.pending.find(secret[:8])
            while start >= 0:
                available = self.pending[start:]
                if len(available) < len(secret) and secret.startswith(available): cut = min(cut, start)
                if self.pending.startswith(secret, start) and start < cut < start + len(secret): cut = start
                start = self.pending.find(secret[:8], start + 1)
        for pattern in PATTERNS:
            for match in pattern.finditer(self.pending):
                if match.start() < cut < match.end(): cut = match.start()
        ready, self.pending = self.pending[:cut], self.pending[cut:]
        if len(self.pending) > self.MAX_PENDING:
            self.pending = ''
            raise ValueError('Output could not be safely filtered within the secret-buffer limit')
        return self.redactor.text(ready)

    def finish(self):
        result, self.pending = self.redactor.text(self.pending), ''
        return result
