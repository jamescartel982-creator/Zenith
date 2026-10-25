"""Compare real native generation through the old/new harness, without promotion."""
import argparse
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path
import tempfile
import time
from agent.checkpoints import inventory
from agent.config import Settings
from agent.model_registry import build_registry
from agent.orchestration import Orchestrator
from agent.paths import config_file
from agent.providers import HuggingFaceProvider
from agent.research import verify_bundle
from agent.task_router import RoutingRequest

CASES = [
    {'id': 'arithmetic', 'prompt': 'What is 2 plus 2? Answer with just the digit.', 'expected': '4'},
    {'id': 'geography', 'prompt': 'What is the capital of France? Answer with just the city.', 'expected': 'Paris'},
]


def check(bundle=None):
    settings = replace(Settings(), provider='huggingface', max_new_tokens=32, temperature=0, offline=True)
    before = inventory(settings.adapter) if settings.adapter else None
    profile = config_file()
    profile_hash = hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None
    if bundle:
        verify_bundle(bundle)
    old = HuggingFaceProvider(settings)
    started = time.perf_counter(); old.load(); cold = time.perf_counter() - started
    registry = build_registry(settings)
    native = registry.adapters[registry.get(registry.native_key).provider]
    native.providers[registry.native_key] = old  # Same loaded weights, fair warm harness comparison.
    orchestrator = Orchestrator(registry)
    rows = []
    for case in CASES:
        messages = [{'role': 'user', 'content': case['prompt']}]
        started = time.perf_counter(); baseline, _ = old.generate(messages); baseline_ms = (time.perf_counter()-started)*1000
        started = time.perf_counter(); candidate, trace = orchestrator.run(messages, RoutingRequest(max_output_tokens=32, timeout=120)); routed_ms = (time.perf_counter()-started)*1000
        if baseline != candidate.text or trace['answer_member'] != registry.native_key:
            raise AssertionError('Native harness changed the real model response')
        rows.append({'id': case['id'], 'prompt': case['prompt'], 'baseline_response': baseline, 'routed_response': candidate.text,
            'exact_match': baseline == candidate.text, 'expected_answer_passed': candidate.text.strip().rstrip('.') == case['expected'],
            'baseline_ms': round(baseline_ms, 3), 'routed_ms': round(routed_ms, 3), 'usage': candidate.usage,
            'trace': trace})
    if before is not None and inventory(settings.adapter) != before:
        raise AssertionError('Original checkpoint changed')
    if (hashlib.sha256(profile.read_bytes()).hexdigest() if profile.exists() else None) != profile_hash:
        raise AssertionError('Saved configuration changed')
    if bundle:
        verify_bundle(bundle)
    return {'schema_version': 1, 'purpose': 'Native harness compatibility smoke, not a frontier capability or speed benchmark',
        'cases_sha256': hashlib.sha256(json.dumps(CASES, sort_keys=True).encode()).hexdigest(),
        'model': settings.model, 'revision': settings.revision, 'adapter_sha256': before['adapter_model.safetensors']['sha256'] if before else None,
        'settings': {'temperature': 0, 'max_new_tokens': 32, 'cpu_threads': settings.cpu_threads, 'offline': True},
        'device': str(old.model.device), 'cold_load_seconds': round(cold, 3), 'results': rows,
        'external_api_calls': 0, 'weights_unchanged': True, 'profile_unchanged': True,
        'limitations': ['Two probes do not establish broad quality, instruction following or reasoning accuracy.',
            'One warm sample per prompt/path; no statistically supported performance improvement is claimed.',
            'No GPU available; VRAM, GPU utilization, provider pricing and proprietary-model inference were not measured.',
            'Orchestration buffers complete replies; routed latency is not streaming time to first token.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check(args.bundle)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream: stream.write(text)
    print(text)


if __name__ == '__main__': main()
