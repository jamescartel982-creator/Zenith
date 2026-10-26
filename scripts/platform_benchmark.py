"""Measure the unchanged selected local model via legacy chat and queued task APIs.

Uses temporary account/data only, cached existing weights and offline inference.
This is a compatibility/latency smoke, not a quality or promotion benchmark.
"""
import argparse
from dataclasses import replace
import hashlib
import gc
import json
from pathlib import Path
import statistics
import tempfile
import time
from uuid import uuid4

from scripts.platform_protection import capture, compare, check_destination


def source_hash():
    root = Path(__file__).resolve().parents[1]
    files = sorted((root/'agent').rglob('*.py')) + [Path(__file__).resolve()]
    return hashlib.sha256(b'\n'.join(str(p.relative_to(root)).encode() + b':' + hashlib.sha256(p.read_bytes()).hexdigest().encode() for p in files)).hexdigest()


def measure(samples=3, bundle=None):
    from agent.config import Settings
    original = Settings()
    if bundle is None:
        if original.provider != 'huggingface' or not original.adapter:
            raise ValueError('Select the existing trained HF adapter or an explicit verified bundle for this offline benchmark')
        try:
            return _measure(samples, original, original)
        finally:
            gc.collect()
    from agent.research import materialize, verify_bundle
    source, manifest = verify_bundle(bundle)
    if manifest['base_model'] != original.model:
        raise ValueError('The test bundle must preserve the configured base model identity')
    with tempfile.TemporaryDirectory(prefix='zenith-platform-checkpoint-') as folder:
        selected = replace(original, provider='huggingface', model=manifest['base_model'],
                           revision=manifest['base_revision'], adapter=str(Path(folder)/'verified-adapter'),
                           checkpoint_receipt='')
        materialize(source, selected.adapter)
        try:
            report = _measure(samples, original, selected)
            verify_bundle(source)
            report['selection'] = 'explicit-byte-verified-inactive-bundle; no profile activation'
            return report
        finally:
            # Release model/storage cycles before temporary safetensors cleanup on Windows.
            gc.collect()


def _measure(samples, original, selected):
    from fastapi.testclient import TestClient
    from agent.config import Settings
    from agent.core import Agent
    from agent.paths import config_file
    from agent.platform_config import PlatformConfig
    from agent.server import create_app
    before = capture(original, config_file())
    selected_before = capture(selected)
    fixtures = Path(__file__).resolve().parents[1]/'agent/evaluation/platform-v1.json'
    prompt = json.loads(fixtures.read_text())['native_prompt']
    records = []
    with tempfile.TemporaryDirectory(prefix='zenith-platform-benchmark-') as folder:
        settings = replace(selected, data_dir=folder, api_token='', offline=True, allow_external=False,
                           temperature=0, max_new_tokens=32, fast_max_new_tokens=32,
                           cpu_threads=2, platform=PlatformConfig(enabled=True, runtime_enabled=True))
        agent = Agent(settings)
        started = time.perf_counter(); agent.provider.load()
        cold_load = time.perf_counter()-started
        app = create_app(settings, agent)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.post('/api/account/register', json={'username': 'benchmark', 'display_name': 'Benchmark',
                                                               'password': 'temporary benchmark account password'})
            response.raise_for_status()
            for index in range(samples):
                # Alternate path order to reduce fixed ordering bias; still a small smoke.
                pair = {}
                for mode in (['legacy', 'queued'] if index % 2 == 0 else ['queued', 'legacy']):
                    started = time.perf_counter()
                    if mode == 'legacy':
                        response = client.post('/api/chat', json={'session_id': str(uuid4()), 'message': prompt})
                        response.raise_for_status(); result = response.json()
                    else:
                        response = client.post('/api/platform/tasks', json={'kind': 'chat', 'message': prompt})
                        response.raise_for_status(); task_id = response.json()['id']
                        deadline = time.monotonic()+settings.platform.task_seconds+10
                        while time.monotonic() < deadline:
                            response = client.get('/api/platform/tasks/'+task_id)
                            response.raise_for_status(); task = response.json()
                            if task['status'] in {'completed', 'failed', 'cancelled', 'needs_reconciliation'}:
                                break
                            time.sleep(0.02)
                        else:
                            raise RuntimeError('Queued model smoke exceeded its deadline')
                        if task['status'] != 'completed':
                            raise RuntimeError('Queued model smoke did not complete: '+str(task['error']))
                        result = task['result']
                    pair[mode] = {'end_to_end_ms': round((time.perf_counter()-started)*1000, 3),
                                  'response': app.state.platform.filter_output(result['response']),
                                  'model': result['model'], 'performance': result.get('performance')}
                pair['sample'] = index+1
                pair['exact_output_parity'] = pair['legacy']['response'] == pair['queued']['response']
                records.append(pair)
        import torch
        device = str(agent.provider.model.device)
    after = capture(original, config_file())
    if not compare(before, after):
        raise RuntimeError('Protected model/profile changed during the smoke')
    if not compare(selected_before, capture(selected)):
        raise RuntimeError('The selected test checkpoint changed during the smoke')
    return {'purpose': 'Actual existing-checkpoint ASGI/queued-chat compatibility and latency smoke',
            'source_commit': before['source_commit'], 'python_sources_sha256': source_hash(),
            'fixture_sha256': hashlib.sha256(fixtures.read_bytes()).hexdigest(),
            'model': selected.model, 'revision': selected.revision,
            'adapter_sha256': selected_before['adapter_files'].get('adapter_model.safetensors'),
            'device': device, 'cpu_threads': settings.cpu_threads, 'temperature': 0, 'max_new_tokens': 32,
            'cold_load_seconds': round(cold_load, 3), 'samples': records,
            'median_end_to_end_ms': {mode: round(statistics.median(r[mode]['end_to_end_ms'] for r in records), 3)
                                     for mode in ('legacy', 'queued')},
            'protected_model_and_profile_unchanged': True, 'external_model_calls': 0,
            'not_measured': ['general accuracy', 'task completion across domains', 'GPU utilization', 'peak RAM/VRAM',
                             'concurrent throughput', 'sandbox escape resistance', 'channel E2E', 'provider cost'],
            'limitations': ['Small warm sample; no speed/quality improvement claim',
                           'ASGI transport, not internet/network load testing',
                           'Queued latency includes admission and 20ms polling',
                           'Startup loading and blocking provider calls have cooperative cancellation limits']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--bundle', type=Path, help='Test an explicitly verified existing inactive bundle in a temporary directory; never activate it')
    args = parser.parse_args()
    if not 1 <= args.samples <= 10:
        parser.error('Choose one to ten paired smoke samples')
    from agent.config import Settings
    from agent.paths import config_file
    try:output=check_destination(Settings(),config_file(),args.output)
    except ValueError as exc:parser.error(str(exc))
    result = measure(args.samples, args.bundle)
    with output.open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'samples': args.samples, 'medians_ms': result['median_end_to_end_ms'],
                      'weights_unchanged': True, 'result': str(output)}))


if __name__ == '__main__': main()
