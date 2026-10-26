"""Bound single-model admission; cancellation never releases a running model."""
from dataclasses import dataclass
import threading
import time


class InferenceCancelled(RuntimeError):
    pass


class ContextExceeded(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    context_tokens: int = 2048
    max_output_tokens: int = 256
    deadline_seconds: float = 120

    def __post_init__(self):
        if not 128 <= self.context_tokens <= 32768 or not 1 <= self.max_output_tokens <= 4096 or not 0.05 <= self.deadline_seconds <= 900:
            raise ValueError('Invalid inference limits')


class Cancellation:
    def __init__(self, seconds):
        self.event = threading.Event()
        self.deadline = time.monotonic() + seconds

    def cancelled(self):
        return self.event.is_set() or time.monotonic() >= self.deadline

    def check(self):
        if self.cancelled():
            raise InferenceCancelled('Inference cancelled or deadline exceeded')
