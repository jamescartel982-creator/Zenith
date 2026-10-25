"""Opt-in, bounded orchestration. Default native Zenith keeps its existing weights."""
import argparse
from dataclasses import replace
import json
import os
from threading import Event, Lock
import time
from .model_registry import build_registry
from .provider_adapters.common import AdapterError, CallContext, Cancelled, text_messages
from .response_verifier import parse_review, review_messages, validate_answer
from .task_router import MODES, RoutingRequest, TaskRouter, estimate_cost


class Orchestrator:
    def __init__(self, registry, clock=time.monotonic):
        self.registry, self.clock = registry, clock
        self.router = TaskRouter(registry)
        self.breakers = {}
        self.lock = Lock()

    def run(self, messages, request=None, cancel=None, security=None):
        request, cancel = request or RoutingRequest(), cancel or Event()
        messages = text_messages(messages)
        if request.input_modalities != ('text',) or request.output_modalities != ('text',) or request.require_tools:
            raise ValueError('Phase 1/2 executes text only; tool/modality metadata does not enable execution')
        if request.mode == 'security-research':
            # The trusted caller supplies execution controls and a live account session.
            # A prompt, registry entry, API key or model response cannot satisfy this.
            if not isinstance(security, dict) or set(security) != {'controls', 'user_id', 'token', 'capability', 'target'}:
                raise PermissionError('Security research requires verified owner/MFA capability and target scope')
            scope = security['controls'].require(security['user_id'], security['token'], security['capability'])
            from .execution import authorized_addresses
            if scope.get('kind') != 'network' or not isinstance(security['target'], dict):
                raise PermissionError('An explicit authorized network target is required')
            authorized_addresses(security['target'].get('host'), security['target'].get('port'), scope)
        if not self.lock.acquire(blocking=False):
            raise RuntimeError('Orchestrator is busy')
        try:
            return self._run(messages, request, cancel, security)
        finally:
            self.lock.release()

    def _run(self, messages, request, cancel, security):
        deadline = self.clock() + request.timeout
        context = CallContext(deadline, cancel, request.max_output_tokens, clock=self.clock)
        context.check()
        trace = {'mode': request.mode, 'members': [], 'verification': {'status': 'not_requested', 'calibrated_confidence': None},
                 'deadline_semantics': 'cooperative; checked between I/O reads and generation steps; model loading and blocking I/O can delay cancellation',
                 'external_allowed': request.allow_external and request.mode not in {'native', 'local-only', 'security-research'},
                 'estimated_provider_cost_usd': 0.0, 'degraded': False, 'models_merged': False}
        # Only explicit opt-in invokes account discovery. No online discovery in native/local-only mode.
        if trace['external_allowed']:
            for provider in sorted({r.provider for r in self.registry.records.values() if r.configured and not r.local}):
                context.check()
                self.registry.refresh(provider, context)
        input_tokens = sum(len(m['content'].encode('utf-8')) + 32 for m in messages)
        selected = self.router.select(request, input_tokens)
        if not selected:
            raise AdapterError('no_eligible_model')
        attempts = 0
        spent = 0.0
        usage_records = []

        def invoke(candidates, original, stage):
            nonlocal attempts, spent
            for record in candidates:
                for retry in range(request.retries + 1):
                    context.check()
                    if attempts >= request.max_calls:
                        return None
                    state = self.breakers.get(record.key, {'failures': 0, 'until': 0})
                    if self.clock() < state['until']:
                        break
                    limit = min(request.max_output_tokens, record.capabilities.max_output_tokens or request.max_output_tokens)
                    estimated_input = sum(len(m['content'].encode('utf-8')) + 32 for m in original)
                    if not record.local and record.capabilities.context_window is not None and estimated_input + limit > record.capabilities.context_window:
                        break
                    estimate = estimate_cost(record, estimated_input, limit)
                    if request.max_cost_usd is not None and (estimate is None or spent + estimate > request.max_cost_usd):
                        break
                    effort = {'fast': 'low', 'standard': 'medium', 'deep': 'high', 'research': 'high'}[request.effort]
                    call = CallContext(deadline, cancel, limit, effort, self.clock)
                    attempts += 1
                    started = self.clock()
                    item = {'id': record.key, 'provider': record.provider, 'model': record.model_id, 'stage': stage, 'attempt': retry + 1, 'status': 'failed'}
                    trace['members'].append(item)
                    if estimate is None:
                        trace['estimated_provider_cost_usd'] = None
                    else:
                        spent += estimate  # Reserve even failed calls: an upstream may already have billed them.
                    try:
                        result = self.registry.adapters[record.provider].generate(record, original, call)
                        call.check()
                        result.text = validate_answer(result.text)
                        elapsed = (self.clock() - started) * 1000
                        self.registry.observe(record.key, elapsed)
                        item.update(status='ok', latency_ms=round(elapsed, 2), usage=result.usage)
                        usage_records.append(item)
                        self.breakers[record.key] = {'failures': 0, 'until': 0}
                        return record, result
                    except Cancelled:
                        item['reason'] = 'request_cancelled'
                        raise
                    except Exception as exc:
                        code = exc.code if isinstance(exc, AdapterError) else 'generation_failed'
                        item.update(reason=code, latency_ms=round((self.clock() - started) * 1000, 2))
                        usage_records.append(item)
                        trace['degraded'] = True
                        failures = state['failures'] + 1
                        denied = code in {'access_denied', 'credential_missing'}
                        self.breakers[record.key] = {'failures': failures, 'until': self.clock() + 30 if failures >= 2 or denied else 0}
                        if denied:
                            self.registry.records[record.key] = replace(record, availability='unavailable', access='Inference denied; explicit refresh required')
                        if code == 'deadline_exceeded':
                            raise
                        if not isinstance(exc, AdapterError) or not exc.retryable:
                            break
            return None

        first = invoke(selected, messages, 'draft')
        if first is None:
            raise AdapterError('all_eligible_models_failed')
        chosen, completion = first
        if request.mode == 'collaborative':
            others = [r for r in selected if r.key != chosen.key]
            second = invoke(others, messages, 'independent_draft') if others else None
            if second:
                from .model_federation import synthesis_messages
                drafts = [{'model': r.key, 'text': c.text} for r, c in (first, second)]
                synthesis = invoke(selected, synthesis_messages(messages, drafts), 'synthesis')
                if synthesis:
                    chosen, completion = synthesis
                else:
                    trace['degraded'] = True
            else:
                trace['degraded'] = True
                trace['collaboration'] = 'Only one successful authorized model; returning its draft'
        if request.mode in {'deep', 'research'} or request.effort in {'deep', 'research'}:
            reviewers = sorted(selected, key=lambda r: r.key == chosen.key)
            review = invoke(reviewers, review_messages(messages, completion.text), 'verification')
            if review:
                trace['verification'] = parse_review(review[1].text) | {'reviewer': review[0].key}
            else:
                trace['verification'] = {'status': 'unverified', 'calibrated_confidence': None, 'issues': ['Verification budget exhausted or reviewer unavailable']}
            if trace['verification']['status'] != 'model_review_passed':
                trace['degraded'] = True
        context.check()
        if security:
            scope = security['controls'].require(security['user_id'], security['token'], security['capability'])
            from .execution import authorized_addresses
            authorized_addresses(security['target']['host'], security['target']['port'], scope)
        trace.update(answer_member=chosen.key, answer_stage=next(i['stage'] for i in reversed(trace['members']) if i['id'] == chosen.key and i['status'] == 'ok' and i['stage'] != 'verification'),
                     selected_members=[r.key for r in selected], calls=attempts,
                     training_eligible=all(self.registry.get(i['id']).local for i in trace['members']),
                     estimated_provider_cost_usd=round(spent, 8) if trace['estimated_provider_cost_usd'] is not None else None)
        from .efficiency import combine_usage
        completion.usage = combine_usage(usage_records)
        return completion, trace


class OrchestratedProvider:
    """Existing generate/stream contract, opt-in through AI_PROVIDER=orchestrated."""
    def __init__(self, settings, registry=None):
        self.settings = settings
        self.registry = registry or build_registry(settings)
        self.orchestrator = Orchestrator(self.registry)
        self.last_usage, self.last_deliberation = None, None
        self.last_model_label = 'Zenith native'

    def _run(self, messages, cancel):
        self.last_usage = self.last_deliberation = None
        result, trace = self.orchestrator.run(messages, RoutingRequest(mode=self.settings.orchestration_mode,
            allow_external=self.settings.allow_external and not self.settings.offline,
            max_output_tokens=self.settings.max_new_tokens, effort=self.settings.reasoning_effort), cancel)
        self.last_usage, self.last_deliberation = result.usage, trace
        self.last_model_label = trace['answer_member']
        return result

    def generate(self, messages):
        result = self._run(messages, Event())
        return result.text, result.used_messages

    def stream(self, messages, cancel):
        # Full-response buffering is explicit; never fabricate TTFT for this path.
        result = self._run(messages, cancel)
        if not cancel.is_set():
            yield result.text, result.used_messages

    def team_info(self):
        return {'mode': 'orchestrated', 'members': [{'id': r.key, 'name': r.model_id, 'provider': r.provider,
            'model': r.model_id, 'role': 'general'} for r in list(self.registry.records.values()) if r.routable],
            'synthesizer': None, 'limits': {'max_experts': 2}, 'registry': self.registry.public()}


def main():
    from .config import Settings
    from .core import Agent
    from uuid import uuid4
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt')
    parser.add_argument('--mode', choices=MODES, default='native')
    parser.add_argument('--effort', choices=('fast', 'standard', 'deep', 'research'), default='standard')
    parser.add_argument('--allow-external', action='store_true', help='Explicitly permit sending this conversation context to configured provider accounts')
    args = parser.parse_args()
    settings = replace(Settings(), provider='orchestrated', orchestration_mode=args.mode, reasoning_effort=args.effort, allow_external=args.allow_external)
    result = Agent(settings).answer(args.prompt, str(uuid4()), response_mode='thorough')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
