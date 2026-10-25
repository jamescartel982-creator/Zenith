"""Privacy/capability filters precede optional measured routing preferences."""
from dataclasses import dataclass
import math

MODES = ('native', 'fast', 'deep', 'coding', 'research', 'collaborative', 'local-only', 'security-research')


@dataclass(frozen=True)
class RoutingRequest:
    mode: str = 'native'
    allow_external: bool = False
    context_tokens: int = 0  # Explicit minimum if known; otherwise conservative byte upper bound.
    require_tools: bool = False
    input_modalities: tuple = ('text',)
    output_modalities: tuple = ('text',)
    max_cost_usd: float | None = None
    max_output_tokens: int = 256
    effort: str = 'standard'
    timeout: float = 120
    max_calls: int = 6
    retries: int = 1

    def __post_init__(self):
        if self.mode not in MODES or self.effort not in {'fast', 'standard', 'deep', 'research'}:
            raise ValueError('Unknown orchestration mode or reasoning effort')
        if type(self.context_tokens) is not int or not 0 <= self.context_tokens <= 10000000:
            raise ValueError('Invalid context requirement')
        if type(self.max_output_tokens) is not int or not 1 <= self.max_output_tokens <= 4096:
            raise ValueError('Invalid output budget')
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 600 or type(self.max_calls) is not int or not 1 <= self.max_calls <= 12 or self.retries not in {0, 1, 2}:
            raise ValueError('Invalid bounded inference budget')
        if self.max_cost_usd is not None and (not math.isfinite(self.max_cost_usd) or self.max_cost_usd < 0):
            raise ValueError('Invalid maximum cost')


def estimate_cost(record, input_tokens, output_tokens):
    if record.local:
        return 0.0  # Provider bill only; local electricity/compute costs are unmeasured.
    pricing = record.capabilities.pricing
    incoming, outgoing = pricing.get('input_usd_per_million'), pricing.get('output_usd_per_million')
    if type(incoming) not in {int, float} or type(outgoing) not in {int, float}:
        return None
    return (input_tokens * incoming + output_tokens * outgoing) / 1000000


class TaskRouter:
    def __init__(self, registry):
        self.registry = registry

    def select(self, request, input_tokens=0):
        eligible = []
        for record in self.registry.records.values():
            if not record.routable:
                continue
            if request.mode in {'native', 'security-research'} and record.key != self.registry.native_key:
                continue
            if (request.mode == 'local-only' or not request.allow_external) and not record.local:
                continue
            caps = record.capabilities
            if not set(request.input_modalities) <= set(caps.input_modalities) or not set(request.output_modalities) <= set(caps.output_modalities):
                continue
            if request.require_tools and caps.tools is not True:
                continue
            # Unknown windows cannot satisfy an explicit minimum requirement.
            if request.context_tokens and (caps.context_window is None or caps.context_window < request.context_tokens + request.max_output_tokens):
                continue
            if not record.local and caps.context_window is not None and caps.context_window < input_tokens + request.max_output_tokens:
                continue
            estimated = estimate_cost(record, input_tokens, request.max_output_tokens)
            if request.max_cost_usd is not None and (estimated is None or estimated > request.max_cost_usd):
                continue
            eligible.append(record)
        def priority(record):
            metric = self.registry.metrics.get(record.key, {})
            native = record.key == self.registry.native_key
            if request.mode == 'fast':
                return (metric.get('latency_ms', float('inf')), not native, record.key)
            if request.mode == 'coding':
                return ('coding' not in record.capabilities.tags, -metric.get('quality', -1), not native, record.key)
            return (-metric.get('quality', -1), not native, record.key)
        return sorted(eligible, key=priority)
