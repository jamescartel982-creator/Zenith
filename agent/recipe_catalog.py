"""Explicit, compact installation of 100,000 labeled generated workflow recipes."""
import argparse
import hashlib
import json
import re
import shutil
import time

from . import recipe_definitions_v1 as grammar
from .skills import _library, validate_profile

PACK = 'generated-recipes-v1'


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_recipe_packs'").fetchone() is not None


def installed_count(db, include_admin=True):
    if not exists(db):
        return 0
    return db.execute('SELECT COUNT(*) FROM generated_recipes' +
        ('' if include_admin else ' WHERE subject<?'), () if include_admin else (grammar.PUBLIC_SUBJECTS,)).fetchone()[0]


def cursor_start(after):
    """Lower bound for any lexicographic cursor, without materializing identifiers."""
    low, high = 0, grammar.TOTAL
    while low < high:
        middle = (low + high) // 2
        if grammar.PREFIX + f'{middle:05d}' <= after:
            low = middle + 1
        else:
            high = middle
    return low


class RecipeCatalog:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _pack(db):
        if not exists(db):
            return None
        row = db.execute('SELECT * FROM generated_recipe_packs WHERE id=?', (PACK,)).fetchone()
        if row and row['definition_sha256'] != grammar.fingerprint():
            raise ValueError('Generated recipe definitions differ from the installed version; do not silently reinterpret this pack')
        return row

    def status(self, include_admin=False):
        with self.store.connect() as db:
            row = self._pack(db)
            count = installed_count(db, include_admin) if row else 0
        return {'installed_profiles': count, 'kind': 'generated-workflow-recipes',
                'generator_version': grammar.VERSION, 'notice': grammar.NOTICE,
                'independently_evaluated': 0, 'training_performed': False}

    def get(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(re.escape(grammar.PREFIX) + r'[0-9]{5}', identifier):
            raise ValueError('Unknown skill')
        index = int(identifier[len(grammar.PREFIX):])
        with self.store.connect() as db:
            if not self._pack(db) or not db.execute('SELECT 1 FROM generated_recipes WHERE idx=?', (index,)).fetchone():
                raise ValueError('Unknown skill')
        value = grammar.render(index)
        resources = _library()['resources']
        validate_profile(value, {item['id'] for item in resources})
        return {**value, 'resources': [item for item in resources if item['id'] in value['resource_ids']],
                'origin': 'generated-workflow-recipe', 'generated': True,
                'generator_version': grammar.VERSION, 'notice': grammar.NOTICE,
                'independently_evaluated': False}

    def search_rows(self, query, category, after, limit, include_admin):
        # SkillCatalog validates the public query/cursor/page bounds first.
        terms = list(dict.fromkeys(re.findall(r'[^\W_]{2,}', query.casefold())))[:12]
        if query.strip() and not terms:
            return []
        start = cursor_start(after)
        if start >= grammar.TOTAL:
            return []
        clauses, values = ['idx>=?'], [start]
        exact = re.fullmatch(re.escape(grammar.PREFIX) + r'([0-9]{5})', query.strip().casefold())
        if exact:
            clauses.append('idx=?'); values.append(int(exact.group(1))); terms = []
        if not include_admin or category == 'general':
            clauses.append('subject<?'); values.append(grammar.PUBLIC_SUBJECTS)
        if category == 'security':
            clauses.append('subject>=?'); values.append(grammar.PUBLIC_SUBJECTS)
        dimensions = ('subject', 'workflow', 'lens', 'audience')
        with self.store.connect() as db:
            if not self._pack(db):
                return []
            for term in terms:
                matches = db.execute('SELECT dimension,slot FROM generated_recipe_terms WHERE generated_recipe_terms MATCH ?',
                                     ('"' + term + '"',)).fetchall()
                # The shared generation label is searchable for every recipe.
                if any(int(row['dimension']) == 4 for row in matches):
                    continue
                alternatives = []
                for number, column in enumerate(dimensions):
                    slots = [int(row['slot']) for row in matches if int(row['dimension']) == number]
                    if slots:
                        alternatives.append(column + ' IN (' + ','.join('?' for _ in slots) + ')')
                        values.extend(slots)
                if not alternatives:
                    return []
                clauses.append('(' + ' OR '.join(alternatives) + ')')
            rows = db.execute('SELECT idx FROM generated_recipes WHERE ' + ' AND '.join(clauses) +
                              ' ORDER BY idx LIMIT ?', (*values, limit)).fetchall()
        result = []
        for row in rows:
            profile = grammar.render(row['idx'])
            result.append({key: profile[key] for key in ('id', 'name', 'category', 'access', 'deliverable')}
                          | {'generated': True, 'origin': 'generated-workflow-recipe'})
        return result

    def install(self, approved=False):
        if approved is not True:
            raise PermissionError('Explicit local approval is required to install generated recipes')
        from .skill_catalog import CAPACITY, imported_instruction
        from .curriculum import SECRET_PATTERN
        started = time.perf_counter()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._pack(db)
            if row:
                if installed_count(db) != grammar.TOTAL:
                    raise ValueError('Installed generated pack is incomplete; restore or explicitly remove it before reinstalling')
                return self._receipt(row, already_installed=True)
            if grammar.TOTAL != 100000 or (len(grammar.SUBJECTS), len(grammar.WORKFLOWS), len(grammar.LENSES), len(grammar.AUDIENCES)) != (100, 25, 10, 4):
                raise ValueError('Unexpected generated recipe dimensions')
            if shutil.disk_usage(self.store.path.parent).free < 64 * 1024 * 1024:
                raise ValueError('Allow at least 64 MiB of free disk space before installing generated recipes')
            imported = db.execute("SELECT 1 FROM sqlite_master WHERE name='skill_pack_profiles'").fetchone()
            if imported:
                count = db.execute('SELECT COUNT(*) FROM skill_pack_profiles').fetchone()[0]
                if count + grammar.TOTAL > CAPACITY:
                    raise ValueError('Existing imported profiles leave insufficient capacity; no profiles were removed')
                if db.execute("SELECT 1 FROM skill_pack_profiles WHERE id LIKE 'x-recipes-%' LIMIT 1").fetchone():
                    raise ValueError('The generated recipe namespace is occupied; existing profiles are preserved')
            if grammar.TOTAL > CAPACITY:
                raise ValueError('Insufficient skill catalog capacity')
            db.execute('''CREATE TABLE IF NOT EXISTS generated_recipe_packs (
                id TEXT PRIMARY KEY, definition_sha256 TEXT NOT NULL,
                rendered_sha256 TEXT NOT NULL, recipe_count INTEGER NOT NULL, installed REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS generated_recipes (
                idx INTEGER PRIMARY KEY CHECK(idx>=0 AND idx<100000),
                subject INTEGER NOT NULL, workflow INTEGER NOT NULL,
                lens INTEGER NOT NULL, audience INTEGER NOT NULL)''')
            for column in ('subject', 'workflow', 'lens', 'audience'):
                db.execute(f'CREATE INDEX IF NOT EXISTS generated_recipe_{column} ON generated_recipes({column},idx)')
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS generated_recipe_terms USING fts5(dimension UNINDEXED,slot UNINDEXED,text)')
            digest = hashlib.sha256()
            definition_hash = grammar.fingerprint()
            seen = set()
            resources = {item['id'] for item in _library()['resources']}
            # Each actual entry is rendered/validated, then stored as its immutable
            # grammar coordinates. No temporary 100 MB JSONL copy or duplicate DB.
            for index in range(grammar.TOTAL):
                profile = grammar.render(index)
                validate_profile(profile, resources)
                encoded = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
                if SECRET_PATTERN.search(encoded.decode('utf-8')) or len(imported_instruction(profile)) > 2400:
                    raise ValueError('Generated recipe failed bounded guidance or secret screening')
                content_hash = hashlib.sha256(' '.join(profile['instruction'].casefold().split()).encode('utf-8')).digest()
                if content_hash in seen:
                    raise ValueError('Duplicate generated instructions; do not inflate counts using titles')
                seen.add(content_hash)
                digest.update(encoded); digest.update(b'\n')
                db.execute('INSERT INTO generated_recipes VALUES (?,?,?,?,?)', (index, *grammar.coordinates(index)))
            for dimension, items in enumerate((grammar.SUBJECTS, grammar.WORKFLOWS, grammar.LENSES, grammar.AUDIENCES)):
                for slot, parts in enumerate(items):
                    db.execute('INSERT INTO generated_recipe_terms VALUES (?,?,?)', (dimension, slot, ' '.join(parts)))
            db.execute('INSERT INTO generated_recipe_terms VALUES (4,0,?)', (grammar.NOTICE + ' recipes',))
            from pathlib import Path
            if hashlib.sha256(Path(grammar.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != definition_hash:
                raise ValueError('Recipe definitions changed during installation; installation rolled back')
            db.execute('INSERT INTO generated_recipe_packs VALUES (?,?,?,?,?)',
                (PACK, definition_hash, digest.hexdigest(), grammar.TOTAL, time.time()))
            row = self._pack(db)
            receipt = self._receipt(row, already_installed=False)
        receipt['install_seconds'] = round(time.perf_counter() - started, 3)
        return receipt

    @staticmethod
    def _receipt(row, already_installed):
        return {'pack_id': row['id'], 'installed': row['recipe_count'], 'already_installed': already_installed,
                'definition_sha256': row['definition_sha256'], 'rendered_sha256': row['rendered_sha256'],
                'public_recipes': grammar.PUBLIC_SUBJECTS * 1000, 'admin_recipes': (len(grammar.SUBJECTS) - grammar.PUBLIC_SUBJECTS) * 1000,
                'kind': 'generated-workflow-recipes', 'notice': grammar.NOTICE,
                'license': 'Apache-2.0', 'source': 'locally-authored-frozen-generator-v1',
                'independently_evaluated': 0, 'training_performed': False}

    def remove(self, approved=False):
        if approved is not True:
            raise PermissionError('Explicit local approval is required to remove generated recipes')
        with self.store.connect() as db:
            if not exists(db):
                return 0
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('DELETE FROM generated_recipes').rowcount
            db.execute('DELETE FROM generated_recipe_terms')
            db.execute('DELETE FROM generated_recipe_packs')
        return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'status', 'remove'))
    parser.add_argument('--approve', action='store_true')
    args = parser.parse_args(argv)
    from .config import Settings
    from .storage import Store
    catalog = RecipeCatalog(Store(Settings().data_dir))
    try:
        result = catalog.install(args.approve) if args.action == 'install' else {'removed': catalog.remove(args.approve)} if args.action == 'remove' else catalog.status(include_admin=True)
    except (OSError, ValueError, PermissionError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
