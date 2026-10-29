"""Paired real SQLite searches with/without recipe statistics; no model speed claim."""
import argparse
import ast
from contextlib import contextmanager
import hashlib
import inspect
import json
import platform
from pathlib import Path
import sqlite3
import statistics
import subprocess
import tempfile
import time

BASELINE = 'c11ecbce87fb50ca8c5641f6ce111c382a3cac97'
CASES = (
    ('Python correctness beginner', '', False),
    ('Python compare correctness beginner', '', False),
    ('algebra correctness beginner', '', False),
    ('data quality reproducibility reviewer', '', False),
    ('generated', '', False),
    ('generated', 'x-recipes-89960', False),
    ('x-recipes-99999', '', True),
    ('x-recipes-99999', '', False),
)


def search_method(source):
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RecipeCatalog')
    function = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'search_rows')
    return ast.dump(function, include_attributes=False)


def plan(store, catalog):
    recorded = []
    original = store.connect
    @contextmanager
    def trace():
        with original() as db:
            db.set_trace_callback(recorded.append)
            yield db
    store.connect = trace
    try:
        catalog.search('Python correctness beginner')
    finally:
        store.connect = original
    query = next(sql for sql in recorded if sql.startswith('SELECT idx FROM generated_recipes WHERE'))
    with store.connect() as db:
        return {'sql': query, 'plan': [tuple(row) for row in db.execute('EXPLAIN QUERY PLAN ' + query)]}


def measure(samples=15):
    from agent.recipe_catalog import RecipeCatalog
    from agent.skill_catalog import SkillCatalog
    from agent.storage import Store
    import agent.recipe_catalog as implementation
    reference = subprocess.check_output(['git', 'show', BASELINE + ':agent/recipe_catalog.py'], text=True)
    assert search_method(reference) == search_method(inspect.getsource(implementation)), 'Keep the timed search implementation identical to the pinned baseline'
    watched = ('agent/recipe_catalog.py', 'agent/skill_catalog.py', 'agent/recipe_definitions_v1.py', 'scripts/recipe_search_benchmark.py')
    source = {name: hashlib.sha256(Path(name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in watched}
    with tempfile.TemporaryDirectory(prefix='zenith-paired-recipe-plans-') as folder:
        stores = {key: Store(Path(folder) / key) for key in ('baseline', 'candidate')}
        receipt = RecipeCatalog(stores['baseline']).install(True)
        with stores['baseline'].connect() as first, stores['candidate'].connect() as second: first.backup(second)
        RecipeCatalog(stores['baseline']).optimize(True, reset=True)
        maintenance = RecipeCatalog(stores['candidate']).optimize(True)
        catalogs = {key: SkillCatalog(store) for key, store in stores.items()}
        plans = {key: plan(stores[key], catalogs[key]) for key in stores}
        rows = []
        for query, after, admin in CASES:
            expected = catalogs['baseline'].search(query, after=after, include_admin=admin)
            for _ in range(3):
                for catalog in catalogs.values(): assert catalog.search(query, after=after, include_admin=admin) == expected
            timings = {key: [] for key in stores}
            for sample in range(samples):
                order = ('baseline', 'candidate') if sample % 2 == 0 else ('candidate', 'baseline')
                for key in order:
                    started = time.perf_counter()
                    actual = catalogs[key].search(query, after=after, include_admin=admin)
                    elapsed = (time.perf_counter() - started) * 1000
                    assert actual == expected
                    timings[key].append(elapsed)
            baseline_ms, candidate_ms = (statistics.median(timings[key]) for key in ('baseline', 'candidate'))
            rows.append({'query': query, 'after': after, 'include_admin': admin, 'result_count': len(expected['skills']),
                         'identical_results': True, 'samples_ms': timings, 'baseline_median_ms': baseline_ms,
                         'candidate_median_ms': candidate_ms, 'baseline_over_candidate': baseline_ms / candidate_ms})
        for store in stores.values():
            catalog = RecipeCatalog(store)
            assert catalog.status(True)['installed_profiles'] == 100000
            assert catalog.install(True)['rendered_sha256'] == receipt['rendered_sha256']
            assert SkillCatalog(store).search('x-recipes-99999')['skills'] == []
    assert source == {name: hashlib.sha256(Path(name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in watched}
    return {'baseline_ref': BASELINE, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'source_sha256': source, 'sqlite_version': sqlite3.sqlite_version, 'python': platform.python_version(),
            'platform': platform.system(), 'search_code_matches_baseline': True,
            'comparison': 'Identical data, grammar, schema and search code; default estimates versus collected recipe statistics.',
            'alternating_order': True, 'warmup_per_case_per_side': 3, 'samples_per_case_per_side': samples,
            'recipe_count_per_side': 100000, 'rendered_sha256': receipt['rendered_sha256'],
            'maintenance': maintenance, 'query_plans': plans, 'cases': rows, 'model_calls': 0,
            'limitations': ['Specific SQLite recipe searches on one CPU environment, not general model inference throughput.',
                'Shared-host noise remains despite alternating paired trials; individual timing changes can be inconclusive.',
                'No weights, parameters, tokenizer or user database were changed by this temporary benchmark.',
                'No two-trillion-parameter expansion or 10000x overall speedup was performed.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=15)
    args = parser.parse_args()
    if not 3 <= args.samples <= 50: parser.error('Use 3–50 paired samples')
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    args.output = check_destination(Settings(), config_file(), args.output)
    result = measure(args.samples)
    with args.output.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2); handle.write('\n')
    print(json.dumps(result, indent=2))
