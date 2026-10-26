"""Bound single-model admission; cancellation never releases a running model."""
from dataclasses import dataclass
import asyncio
import threading
import time


class InferenceCancelled(RuntimeError):
    pass


class ContextExceeded(ValueError):
    pass


class ModelBusy(RuntimeError):
    pass


class Admission:
    """Optional bounded FIFO wait; one model worker remains the only owner."""
    def __init__(self,queue_size=0,wait_seconds=120):
        if type(queue_size) is not int or not 0<=queue_size<=8 or not 0.05<=wait_seconds<=900:
            raise ValueError('Use a bounded inference queue')
        self.queue_size,self.wait_seconds=queue_size,wait_seconds
        self.lock=asyncio.Lock()
        self.admitted=0

    def locked(self):
        return self.admitted>0

    async def acquire(self,disconnect):
        if self.admitted>=1+self.queue_size:
            raise ModelBusy('The bounded model queue is full')
        self.admitted+=1
        waiting=asyncio.create_task(self.lock.acquire())
        handed_off=False
        try:
            done,_=await asyncio.wait((waiting,disconnect),timeout=self.wait_seconds,return_when=asyncio.FIRST_COMPLETED)
            if disconnect in done or waiting not in done:
                raise InferenceCancelled('Client disconnected or model queue deadline expired')
            waiting.result()
            handed_off=True
        finally:
            if not handed_off:
                waiting.cancel()
                while not waiting.done():
                    try:await asyncio.shield(waiting)
                    except asyncio.CancelledError:continue
                acquired=not waiting.cancelled() and waiting.exception() is None and waiting.result()
                if acquired:self.lock.release()
                self.admitted-=1

    def release(self):
        self.lock.release()
        self.admitted-=1


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
