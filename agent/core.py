"""Multi-turn chat with immutable inference snapshots for reviewed training."""
from threading import Lock
from .storage import Store
from .providers import make_provider, SYSTEM_PROMPT
from .config import Settings


class Agent:
    def __init__(self, settings=None, provider=None, store=None):
        self.settings = settings or Settings()
        self.store = store or Store(self.settings.data_dir)
        self.provider = provider or make_provider(self.settings)
        # Nonblocking admission prevents an unbounded queue of model requests.
        self.lock = Lock()

    def answer(self, text, session_id):
        text = text.strip()
        if not text or len(text) > 12000:
            raise ValueError("Message must contain 1 to 12000 characters")
        if not self.lock.acquire(blocking=False):
            raise BusyError("Zenith is answering another message. Try again shortly.")
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for turn in self.store.history(session_id):
                messages.extend([
                    {"role": "user", "content": turn["prompt"]},
                    {"role": "assistant", "content": turn["response"]},
                ])
            messages.append({"role": "user", "content": text})
            response, used_messages = self.provider.generate(messages)
            if not isinstance(response, str) or not response.strip():
                raise RuntimeError("The model returned an empty answer. Try a shorter message.")
            response = response.strip()
            turn_id = self.store.add(session_id, text, response, used_messages, self.settings.model_name)
            return {"id": turn_id, "response": response, "model": self.settings.model_name}
        finally:
            self.lock.release()


class BusyError(RuntimeError):
    pass
