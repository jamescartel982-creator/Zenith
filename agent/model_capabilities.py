"""Explicit, conservative metadata. Unknown is never silently treated as supported."""
from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ModelCapabilities:
    input_modalities: tuple[str, ...] = ('text',)
    output_modalities: tuple[str, ...] = ('text',)
    context_window: int | None = None
    max_output_tokens: int | None = None
    tools: bool | None = None
    reasoning_efforts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    pricing: dict = field(default_factory=dict)  # USD / million tokens, when sourced
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRecord:
    provider: str
    model_id: str
    availability: str = 'unavailable'
    configured: bool = False
    local: bool = False
    lifecycle: str = 'unknown'
    access: str = 'Not verified for this account'
    family: str | None = None
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    provenance: str = 'configuration'

    @property
    def key(self):
        return self.provider + ':' + self.model_id

    @property
    def routable(self):
        return self.configured and self.availability in {'configured', 'listed', 'verified'} and self.lifecycle != 'retired'

    def public(self):
        return asdict(self) | {'key': self.key, 'routable': self.routable}


@dataclass
class Completion:
    text: str
    used_messages: list
    usage: dict | None = None
    finish_reason: str | None = None


class ProviderAdapter(Protocol):
    """Trusted application-code plugin interface; never loaded from model text."""
    name: str

    def discover(self, context) -> list[ModelRecord]: ...
    def generate(self, record, messages, context) -> Completion: ...
