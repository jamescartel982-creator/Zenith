"""Validated, searchable source catalog; records never execute or download code."""
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

CATALOG_DIR = Path(__file__).parent / 'catalog'
EXPECTED_COUNTS = {('huggingface', 'model'): 500, ('github', 'model'): 500,
                   ('huggingface', 'dataset'): 100, ('github', 'dataset'): 100}


class Catalog:
    def __init__(self, directory=None, strict=True):
        directory = Path(directory or CATALOG_DIR)
        self.entries, self.snapshots = [], []
        self.lookup = {}
        for (source, kind), expected in EXPECTED_COUNTS.items():
            path = directory / f'{source}_{kind}s.json'
            document = json.loads(path.read_text(encoding='utf-8'))
            if document.get('schema_version') != 1 or document.get('source') != source or document.get('kind') != kind:
                raise ValueError(f'Invalid catalog schema: {path.name}')
            observed = document.get('generated_at')
            if not observed:
                raise ValueError(f'Catalog snapshot needs a timestamp: {path.name}')
            datetime.fromisoformat(observed.replace('Z', '+00:00'))
            entries = document.get('entries')
            if not isinstance(entries, list) or (strict and len(entries) != expected):
                raise ValueError(f'{path.name} must contain {expected} sourced entries')
            for entry in entries:
                self._validate(entry, source, kind)
                key = (source, kind, entry['id'].casefold())
                if key in self.lookup:
                    raise ValueError(f'Duplicate catalog entry: {entry["id"]}')
                self.lookup[key] = entry
                self.entries.append(entry)
            self.snapshots.append({'source': source, 'kind': kind, 'generated_at': observed,
                                   'selection': document.get('selection'), 'count': len(entries)})

    @staticmethod
    def _validate(entry, source, kind):
        if entry.get('source') != source or entry.get('kind') != kind:
            raise ValueError('Catalog entry source/kind mismatch')
        if not isinstance(entry.get('id'), str) or len(entry['id'].split('/')) != 2 or any(not part or part in {'.', '..'} for part in entry['id'].split('/')):
            raise ValueError('Catalog entry needs a canonical owner/name ID')
        expected = f'https://github.com/{entry["id"]}' if source == 'github' else f'https://huggingface.co/{"datasets/" if kind == "dataset" else ""}{entry["id"]}'
        if entry.get('url', '').rstrip('/') != expected:
            raise ValueError('Catalog entry URL must match its source and canonical ID')
        if not entry.get('observed_at') or not entry.get('provenance'):
            raise ValueError('Catalog entries require observation timestamps and provenance')
        if source == 'github' and entry.get('runtime_support') != 'reference_only':
            raise ValueError('A GitHub repository is not a configured inference provider')
        if entry.get('runtime_verified') is True:
            raise ValueError('Catalog popularity metadata cannot assert runtime verification')

    @property
    def counts(self):
        counts = {'models': 0, 'datasets': 0}
        for source, kind in EXPECTED_COUNTS:
            count = sum(e['source'] == source and e['kind'] == kind for e in self.entries)
            counts[f'{source}_{kind}s'] = count
            counts[f'{kind}s'] += count
        return counts

    def get(self, source, kind, identifier):
        try:
            return self.lookup[(source, kind, identifier.casefold())]
        except KeyError as exc:
            raise ValueError('Source is not in the selected catalog') from exc

    def search(self, kind=None, source=None, q='', page=1, page_size=20, configured=()):
        if kind not in {None, 'model', 'dataset'} or source not in {None, 'huggingface', 'github'}:
            raise ValueError('Unknown source or kind filter')
        if page < 1 or not 1 <= page_size <= 100 or len(q) > 200:
            raise ValueError('Invalid pagination or search length')
        words = q.casefold().split()
        rows = []
        for entry in self.entries:
            if (kind and entry['kind'] != kind) or (source and entry['source'] != source):
                continue
            haystack = ' '.join(str(entry.get(key, '')) for key in ('id', 'name', 'description', 'task', 'tags')).casefold()
            if all(word in haystack for word in words):
                rows.append(entry)
        rows.sort(key=lambda e: (e.get('popularity_rank', 100000), e['source'], e['id'].casefold()))
        start = (page - 1) * page_size
        selected = [{**entry, 'configured_for_chat': entry['kind'] == 'model' and entry['source'] == 'huggingface' and entry['id'] in configured}
                    for entry in rows[start:start + page_size]]
        return {'entries': selected, 'total': len(rows), 'page': page, 'page_size': page_size,
                'counts': self.counts, 'snapshots': self.snapshots,
                'generated_at': min(s['generated_at'] for s in self.snapshots)}
