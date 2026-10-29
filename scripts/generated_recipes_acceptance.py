"""Actual 100k generated-recipe install/search/restart/removal, in test-owned state."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def measure():
    from agent.recipe_catalog import RecipeCatalog
    from agent import recipe_definitions_v1 as grammar
    from agent.skill_catalog import SkillCatalog
    from agent.storage import Store
    watched = ['agent/recipe_catalog.py', 'agent/recipe_definitions_v1.py', 'agent/skill_catalog.py', 'agent/core.py']
    source = {name: hashlib.sha256(Path(name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in watched}
    with tempfile.TemporaryDirectory(prefix='zenith-generated-acceptance-') as folder:
        store = Store(folder)
        turn = store.add('preserved-session', 'Original prompt', 'Original answer', [], 'preserved-history')
        recipes = RecipeCatalog(store)
        receipt = recipes.install(True)
        catalog = SkillCatalog(store)
        assert receipt['installed'] == 100000 and catalog.status(True)['generated_profiles'] == 100000
        assert catalog.status()['generated_profiles'] == 90000
        with store.connect() as db:
            rows = db.execute('SELECT COUNT(*),MIN(idx),MAX(idx) FROM generated_recipes').fetchone()
            assert tuple(rows) == (100000, 0, 99999)
            assert db.execute('SELECT response FROM turns WHERE id=?', (turn,)).fetchone()[0] == 'Original answer'
        first = catalog.search('Python correctness beginner', limit=3)
        second = catalog.search('Python correctness beginner', after=first['next'], limit=3)
        assert len(first['skills']) == len(second['skills']) == 3
        assert not {row['id'] for row in first['skills']} & {row['id'] for row in second['skills']}
        timings = []
        queries = ('algebra correctness beginner', 'Python compare correctness beginner',
                   'incident analysis', 'data quality reproducibility reviewer', 'x-recipes-99999')
        for query in queries:
            started = time.perf_counter(); found = catalog.search(query, include_admin=True)
            timings.append((time.perf_counter() - started) * 1000)
            assert found['skills'], query
            assert all(row['generated'] and row['name'].startswith('Generated:') for row in found['skills'])
        assert catalog.search('x-recipes-99999')['skills'] == []
        assert catalog.search(category='security')['skills'] == []
        assert len(catalog.search('x-recipes-99999', include_admin=True)['skills']) == 1
        assert RecipeCatalog(Store(folder)).install(True)['already_installed']
        assert RecipeCatalog(Store(folder)).status(True)['installed_profiles'] == 100000
        database_bytes = store.path.stat().st_size
        rendered = catalog.get('x-recipes-25000')
        assert grammar.NOTICE in rendered['instruction'] and not rendered['independently_evaluated']
        assert recipes.remove(True) == 100000
        assert catalog.status(True)['installed_profiles'] == 0
        assert store.history('preserved-session')[0]['response'] == 'Original answer'
    assert source == {name: hashlib.sha256(Path(name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in watched}
    return {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'source_sha256': source, 'installation': receipt, 'actual_database_rows': 100000,
            'database_bytes': database_bytes, 'queries': list(queries), 'search_samples_ms': timings,
            'search_median_ms': statistics.median(timings), 'restart_persistence': True,
            'restricted_profiles_hidden': True, 'pagination_disjoint': True,
            'explicit_removal_preserved_history': True, 'training_performed': False,
            'limitations': ['100 x 25 x 10 x 4 authored grammar combinations, not 100000 independently evaluated capabilities.',
                'Structural validation and indexing tests do not establish correctness of model answers.',
                'This measurement used removed test-owned state; the separate explicit installation receipt records durable installation.',
                'No 20T model, weight changes or 10000x general inference speedup.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    args.output = check_destination(Settings(), config_file(), args.output)
    result = measure()
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2); handle.write('\n')
    print(json.dumps(result, indent=2))
