"""Opt-in infrastructure settings; no implicit model or backend activation."""
import os
from dataclasses import dataclass


def env_flag(name):
    value = os.getenv(name, '').strip().lower()
    if value not in {'', '0', '1', 'false', 'true', 'no', 'yes'}:
        raise ValueError(f'{name} must be a boolean')
    return value in {'1', 'true', 'yes'}


@dataclass(frozen=True)
class PlatformConfig:
    enabled: bool = False
    runtime_enabled: bool = False
    tools_enabled: bool = False
    memory_enabled: bool = False
    max_pending: int = 32
    per_user_pending: int = 4
    max_steps: int = 8
    task_seconds: int = 120
    lease_seconds: int = 30
    max_tasks: int = 10000

    def __post_init__(self):
        for name in ('enabled', 'runtime_enabled', 'tools_enabled', 'memory_enabled'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'{name} must be boolean')
        for name, low, high in (
            ('max_pending', 1, 256), ('per_user_pending', 1, 32),
            ('max_steps', 1, 8), ('task_seconds', 5, 900),
            ('lease_seconds', 5, 120), ('max_tasks', 1, 100000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{name} must be {low}–{high}')
        if not self.enabled and (self.runtime_enabled or self.tools_enabled or self.memory_enabled):
            raise ValueError('Enable ZENITH_PLATFORM_ENABLED before platform subfeatures')
        if self.tools_enabled and not self.runtime_enabled:
            raise ValueError('Platform tools require the bounded runtime')
        if self.per_user_pending > self.max_pending:
            raise ValueError('Per-account capacity cannot exceed total capacity')

    @classmethod
    def from_env(cls):
        return cls(
            enabled=env_flag('ZENITH_PLATFORM_ENABLED'),
            runtime_enabled=env_flag('ZENITH_PLATFORM_RUNTIME_ENABLED'),
            tools_enabled=env_flag('ZENITH_PLATFORM_TOOLS_ENABLED'),
            memory_enabled=env_flag('ZENITH_PLATFORM_MEMORY_ENABLED'),
            max_pending=int(os.getenv('ZENITH_PLATFORM_MAX_PENDING', '32')),
            per_user_pending=int(os.getenv('ZENITH_PLATFORM_PER_USER_PENDING', '4')),
            task_seconds=int(os.getenv('ZENITH_PLATFORM_TASK_SECONDS', '120')),
        )
