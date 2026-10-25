"""Opt-in policy for ephemeral, offline Python containers, never host execution."""
from dataclasses import dataclass
import os
import re
from threading import BoundedSemaphore

_SLOTS = BoundedSemaphore(1)


def validate_program(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'source'}:
        raise ValueError('Supply only Python source; host paths, commands and environment are forbidden')
    source = arguments['source']
    if not isinstance(source, str) or not 1 <= len(source.encode('utf-8')) <= 8192 or '\x00' in source:
        raise ValueError('Python source must contain 1–8192 UTF-8 bytes without nulls')
    return source


@dataclass(frozen=True)
class SandboxPolicy:
    enabled: bool = False
    image: str = ''
    seconds: int = 10
    output_bytes: int = 2048

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError('Sandbox enablement must be boolean')
        if not isinstance(self.image, str) or (self.image and not re.fullmatch(r'sha256:[0-9a-f]{64}', self.image)):
            raise ValueError('Use an operator-reviewed local immutable Docker image ID')
        if self.enabled and not self.image:
            raise ValueError('An immutable local image ID is required before enabling the sandbox')
        for name, low, high in [('seconds', 1, 30), ('output_bytes', 256, 2048)]:
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError('Invalid sandbox resource budget: ' + name)

    @classmethod
    def from_env(cls):
        raw = os.getenv('ZENITH_SANDBOX_ENABLED', '').strip().lower()
        if raw not in {'', '0', '1', 'true', 'false', 'yes', 'no'}:
            raise ValueError('ZENITH_SANDBOX_ENABLED must be boolean')
        return cls(raw in {'1', 'true', 'yes'}, os.getenv('ZENITH_SANDBOX_IMAGE', ''),
                   int(os.getenv('ZENITH_SANDBOX_SECONDS', '10')))


def run_python(arguments, authority_check):
    """Only called by trusted ExecutionControls; a model cannot supply authority."""
    source = validate_program(arguments)
    authority_check()
    policy = SandboxPolicy.from_env()
    if not policy.enabled:
        raise PermissionError('Isolated Python execution is disabled')
    if not _SLOTS.acquire(blocking=False):
        raise ValueError('The local sandbox execution slot is busy')
    try:
        from .sandbox_docker import DockerSandbox
        return DockerSandbox(policy).run(source, authority_check)
    finally:
        _SLOTS.release()
