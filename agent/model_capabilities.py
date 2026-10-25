"""Explicit, conservative metadata. Unknown is never silently treated as supported."""
from dataclasses import asdict, dataclass, field
import math
from typing import Protocol


def finite_number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


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

    def __post_init__(self):
        for name in ('input_modalities', 'output_modalities', 'reasoning_efforts', 'tags'):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or len(values) > 32 or any(
                    not isinstance(v, str) or not 1 <= len(v) <= 80 for v in values):
                raise ValueError('Invalid model capability labels')
            object.__setattr__(self, name, tuple(values))
        for value in (self.context_window, self.max_output_tokens):
            if value is not None and (type(value) is not int or not 1 <= value <= 10**9):
                raise ValueError('Model token limits must be positive integers or unknown')
        if self.tools is not None and type(self.tools) is not bool:
            raise ValueError('Tool support must be a boolean or unknown')
        if not isinstance(self.extra, dict) or not isinstance(self.pricing, dict):
            raise ValueError('Model metadata must be an object')
        if set(self.pricing) - {'input_usd_per_million', 'output_usd_per_million', 'source'}:
            raise ValueError('Unsupported pricing fields')
        if self.pricing and (not isinstance(self.pricing.get('source'), str) or not self.pricing['source'].startswith('https://')):
            raise ValueError('Pricing requires an HTTPS source reference')
        if any(not finite_number(v) or not 0 <= v <= 1000000 for k, v in self.pricing.items() if k != 'source'):
            raise ValueError('Prices must be finite nonnegative numbers')


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

    def __post_init__(self):
        if not isinstance(self.provider, str) or not 1 <= len(self.provider) <= 100 or ':' in self.provider:
            raise ValueError('Invalid provider identity')
        if not isinstance(self.model_id, str) or not 1 <= len(self.model_id) <= 300 or any(ord(c) < 32 for c in self.model_id):
            raise ValueError('Invalid exact model identity')
        if type(self.local) is not bool or type(self.configured) is not bool:
            raise ValueError('Model locality and configuration require explicit booleans')
        if not isinstance(self.availability, str) or not isinstance(self.lifecycle, str) or self.availability not in {'unavailable', 'unknown', 'configured', 'listed', 'verified'} or self.lifecycle not in {'unknown', 'active', 'deprecated', 'retired'}:
            raise ValueError('Unknown availability or lifecycle status')
        if not isinstance(self.capabilities, ModelCapabilities):
            raise ValueError('Model capabilities require validated metadata')

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
