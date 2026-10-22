"""Diagnose a local install; inference is opt-in and requires cached weights."""
import argparse
import importlib.metadata
import json
import platform
import os
import sqlite3
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from .config import Settings
from .paths import config_file
from .models import model_specs, cache_status


def inspect(settings=None, inference=False):
    settings = settings or Settings()
    checks = []
    def add(name, status, detail):
        checks.append({'name': name, 'status': status, 'detail': detail})
    add('python', 'ok' if sys.version_info >= (3, 10) else 'error', platform.python_version())
    add('platform', 'ok', platform.system() + ' ' + platform.machine())
    add('configuration', 'ok', str(config_file()) + (' (saved)' if config_file().is_file() else ' (defaults/environment)'))
    add('provider', 'ok', settings.provider)
    try:
        if os.name == 'nt':
            import ctypes
            class MemoryStatus(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ('total_phys', 'available_phys', 'total_page', 'available_page', 'total_virtual', 'available_virtual', 'available_extended')]
            memory = MemoryStatus(); memory.length = ctypes.sizeof(memory)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                raise OSError('Memory status unavailable')
            available = memory.available_phys / (1024 ** 3)
        else:
            available = os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / (1024 ** 3)
        recommended = 6 if settings.provider == 'ensemble' else 4
        add('memory', 'warning' if available < recommended else 'ok', f'{available:.1f} GiB available; roughly {recommended} GiB recommended for small CPU models')
    except (OSError, AttributeError, ValueError):
        add('memory', 'warning', 'Available RAM could not be measured; check model hardware requirements.')
    required = ['requests', 'python-dotenv', 'fastapi', 'uvicorn']
    specs = model_specs(settings)
    if any(spec['provider'] == 'huggingface' for spec in specs):
        required += ['torch', 'transformers', 'peft', 'accelerate', 'huggingface-hub']
    elif settings.provider == 'tiny':
        required += ['torch']
    dependencies_ok = True
    for package in required:
        try:
            add(package, 'ok', importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            dependencies_ok = False
            add(package, 'error', 'Missing dependency. Rerun the installer for this provider.')
    try:
        data_dir = Path(settings.data_dir).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.zenith-check-', dir=data_dir) as directory:
            from .storage import Store
            store = Store(directory)
            store.add_document('doctor', 'https://example.com/doctor', 'Zenith storage check')
            if not store.search_documents('Zenith'):
                raise RuntimeError('Full-text index failed')
        add('storage', 'ok', str(data_dir.resolve()) + ' (write/SQLite/FTS checks passed)')
        free = shutil.disk_usage(data_dir).free / (1024 ** 3)
        add('disk', 'warning' if free < 3 else 'ok', f'{free:.1f} GiB free; model downloads need additional space')
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        add('storage', 'error', 'Cannot initialize local storage: ' + type(exc).__name__)
    cached = True
    for spec in specs:
        state = cache_status(spec)
        if state['cached'] is False:
            cached = False
        add('model:' + spec['id'], 'warning' if state['cached'] is False else 'ok', spec['model'] + ' — ' + state['reason'])
    if settings.provider == 'ollama':
        try:
            import requests
            response = requests.get(settings.ollama_url + '/api/tags', timeout=(2, 3))
            response.raise_for_status()
            available = {row['name'] for row in response.json().get('models', [])}
            present = settings.ollama_model in available
            add('ollama', 'ok' if present else 'warning', 'Model available' if present else 'Run ollama pull ' + settings.ollama_model)
        except Exception:
            add('ollama', 'warning', 'Start Ollama, then pull the configured model before chatting.')
    if inference:
        if not dependencies_ok or not cached:
            add('inference', 'error', 'Install dependencies and run zenith models download before this check.')
        else:
            try:
                from .providers import make_provider, SYSTEM_PROMPT
                provider = make_provider(replace(settings, max_new_tokens=24, temperature=0, offline=True))
                answer, _ = provider.generate([{'role': 'system', 'content': SYSTEM_PROMPT},
                                              {'role': 'user', 'content': 'What is 2 plus 2? Answer briefly.'}])
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError('Empty answer')
                add('inference', 'ok', answer[:160])
                trace = getattr(provider, 'last_deliberation', None)
                if isinstance(trace, dict) and trace.get('degraded'):
                    add('team', 'warning', 'Some model stages failed or were skipped; the answer used the available team.')
            except Exception as exc:
                add('inference', 'error', 'Generation failed (' + type(exc).__name__ + '). Check device, weights, context budget, and available memory.')
    return {'ok': all(check['status'] != 'error' for check in checks), 'checks': checks,
            'inference_tested': inference}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Machine-readable report; never includes tokens')
    parser.add_argument('--inference', action='store_true', help='Run a short actual generation with cached weights')
    args = parser.parse_args()
    try:
        report = inspect(inference=args.inference)
    except Exception as exc:
        report = {'ok': False, 'checks': [{'name': 'configuration', 'status': 'error',
                   'detail': 'Configuration could not load: ' + type(exc).__name__}], 'inference_tested': False}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for row in report['checks']:
            print(f'[{row["status"].upper()}] {row["name"]}: {row["detail"]}')
        print('Installation checks passed; review any warnings before chatting.' if report['ok'] else 'Resolve the errors above before chatting.')
        if not args.inference:
            print('Model execution was not tested. Use zenith doctor --inference after caching weights.')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
