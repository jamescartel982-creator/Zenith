"""Best-effort secret redaction; execution authorization never depends on this."""
import re

REDACTED = '[REDACTED]'
PATTERNS = (
    re.compile(r'zenith-admin-[A-Za-z0-9_-]{43}'),
    re.compile(r'\b(?:sk-(?:ant-)?|hf_)[A-Za-z0-9_-]{16,}'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}'),
    re.compile(r'(?i)\b(?:password|api[_-]?key|secret|access[_-]?token)\s*[=:]\s*[\'"]?[^\s\'",;]{8,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END [^-]+-----|$)'),
)


class Redactor:
    def __init__(self, secrets=()):
        self.secrets = tuple(sorted({s for s in secrets if isinstance(s, str) and len(s) >= 8}, key=len, reverse=True))

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
            raise ValueError('Remove credentials before submitting persistent platform input')
        return value
