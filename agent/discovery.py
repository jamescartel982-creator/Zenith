"""On-demand public model discovery. Metadata only; never execute repository code."""
import argparse
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import BoundedSemaphore, Lock
import time
from urllib.parse import parse_qs, quote, urlsplit

import requests
from .paths import zenith_home

ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
LIMIT = 2 * 1024 * 1024


class DiscoveryError(RuntimeError):
    """Sanitized source failure suitable for a browser or terminal."""


def library_path():
    return zenith_home() / 'model-library.json'


def saved_models():
    path = library_path()
    if not path.exists():
        return []
    if path.stat().st_size > 8 * LIMIT:
        raise ValueError('Saved model library is too large')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or not isinstance(value.get('entries'), list):
        raise ValueError('Invalid saved model library')
    rows = value['entries']
    for entry in rows:
        if not isinstance(entry, dict) or entry.get('source') not in {'huggingface', 'github'} or entry.get('kind') != 'model':
            raise ValueError('Invalid saved model entry')
        from .registry import Catalog
        Catalog._validate(entry, entry['source'], 'model')
    return rows


def _text(value, length=1000):
    return value[:length] if isinstance(value, str) else ''


def _number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


class Discovery:
    """Bounded requests to fixed upstream endpoints, with short-lived LRU caching."""
    def __init__(self):
        self._cache = OrderedDict()
        self._lock = Lock()
        self._slots = BoundedSemaphore(2)

    def _json(self, url, params=None):
        if any(os.environ.get(key, '').lower() in {'1', 'true', 'yes'}
               for key in ('HF_HUB_OFFLINE', 'ZENITH_DISCOVERY_OFFLINE')):
            raise DiscoveryError('Online discovery is disabled. Use the bundled catalog or your saved library.')
        key = (url, json.dumps(params, sort_keys=True))
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < 60:
                self._cache.move_to_end(key)
                return deepcopy(cached[1])
        if not self._slots.acquire(blocking=False):
            raise DiscoveryError('Discovery is busy. Wait for the current search and try again.')
        try:
            headers = {'User-Agent': 'Zenith-model-discovery', 'Accept': 'application/json'}
            if url.startswith('https://api.github.com/'):
                headers.update({'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
            started = time.monotonic()
            with requests.get(url, params=params, headers=headers, timeout=(5, 10),
                              stream=True, allow_redirects=False) as response:
                if response.status_code in {403, 429}:
                    raise DiscoveryError('Source access is restricted or rate limited. Wait and retry, or use the bundled catalog.')
                if response.status_code == 404:
                    raise DiscoveryError('Public repository not found. Check its canonical owner/name identifier.')
                if response.status_code != 200:
                    raise DiscoveryError('The source could not complete this request. Try again later.')
                chunks, size = [], 0
                for chunk in response.iter_content(chunk_size=16384):
                    size += len(chunk)
                    if size > LIMIT or time.monotonic() - started > 20:
                        raise DiscoveryError('Source response exceeded the discovery budget. Narrow your search.')
                    chunks.append(chunk)
                data = json.loads(b''.join(chunks))
                next_url = response.links.get('next', {}).get('url', '')
            value = (data, next_url)
            with self._lock:
                self._cache[key] = (time.monotonic(), deepcopy(value))
                self._cache.move_to_end(key)
                while len(self._cache) > 32:
                    self._cache.popitem(last=False)
            return value
        except (requests.RequestException, ValueError, UnicodeError) as exc:
            raise DiscoveryError('Source metadata was unavailable or invalid. Try again or use the bundled catalog.') from exc
        finally:
            self._slots.release()

    @staticmethod
    def _entry(source, kind, raw):
        if not isinstance(raw, dict):
            raise DiscoveryError('Source returned an invalid repository record')
        identifier = raw.get('id' if source == 'huggingface' else 'full_name')
        if not isinstance(identifier, str) or len(identifier) > 200 or not ID.fullmatch(identifier):
            raise DiscoveryError('Source returned an invalid repository identifier')
        tags = raw.get('tags' if source == 'huggingface' else 'topics') or []
        tags = [_text(tag, 200) for tag in tags[:100] if isinstance(tag, str)] if isinstance(tags, list) else []
        card = raw.get('cardData') if isinstance(raw.get('cardData'), dict) else {}
        base = card.get('base_model') or [t[len('base_model:'):] for t in tags
                                            if t.startswith('base_model:') and t.count(':') == 1]
        if isinstance(base, str):
            base = [base]
        bases = [b for b in (base if isinstance(base, list) else []) if isinstance(b, str) and ID.fullmatch(b)][:20]
        fine_tuned = any(t.startswith('base_model:finetune:') for t in tags) or card.get('base_model_relation') == 'finetune'
        license_value = card.get('license')
        if source == 'github':
            license_value = (raw.get('license') or {}).get('spdx_id') if isinstance(raw.get('license'), dict) else None
        if not isinstance(license_value, str):
            license_value = next((t[8:] for t in tags if t.startswith('license:')), 'Unknown — review source')
        now = datetime.now(timezone.utc).isoformat()
        prefix = 'https://github.com/' if source == 'github' else 'https://huggingface.co/' + ('datasets/' if kind == 'dataset' else '')
        entry = {'id': identifier, 'name': identifier, 'source': source, 'kind': kind,
                 'url': prefix + identifier, 'description': _text(raw.get('description') or card.get('description')),
                 'task': _text(raw.get('pipeline_tag'), 100) or ('Repository — review compatibility' if source == 'github' else 'Task not recorded'),
                 'license': license_value[:200], 'tags': tags, 'base_models': bases,
                 'fine_tuned': fine_tuned, 'gated': bool(raw.get('gated', False)),
                 'revision': _text(raw.get('sha'), 64), 'runtime_verified': False,
                 'runtime_support': 'reference_only' if source == 'github' else 'requires_compatibility_review',
                 'observed_at': now, 'provenance': 'Public source API; on-demand metadata, not a runtime verification'}
        for name in ('downloads', 'likes') if source == 'huggingface' else ('stargazers_count',):
            entry['stars' if name == 'stargazers_count' else name] = _number(raw.get(name))
        return entry

    def search(self, source='huggingface', kind='model', q='', page=1, page_size=20, cursor=''):
        if source not in {'huggingface', 'github'} or kind not in {'model', 'dataset'}:
            raise ValueError('Choose Hugging Face or GitHub and a model or dataset')
        if not isinstance(q, str) or len(q) > 200 or not 1 <= page_size <= 50 or not 1 <= page <= 1000000:
            raise ValueError('Invalid discovery query or page')
        if not isinstance(cursor, str) or len(cursor) > 4096:
            raise ValueError('Invalid discovery cursor')
        if source == 'huggingface':
            path = '/api/models' if kind == 'model' else '/api/datasets'
            params = {'search': q, 'sort': 'downloads', 'direction': -1, 'limit': page_size, 'full': 'true'}
            if kind == 'model':
                params['cardData'] = 'true'
            if cursor:
                params['cursor'] = cursor
            rows, link = self._json('https://huggingface.co' + path, params)
            if not isinstance(rows, list) or len(rows) > page_size:
                raise DiscoveryError('Source returned an invalid discovery page')
            next_cursor = ''
            if link:
                parsed = urlsplit(link)
                if parsed.scheme != 'https' or parsed.netloc != 'huggingface.co' or parsed.path != path:
                    raise DiscoveryError('Source returned an invalid continuation link')
                next_cursor = parse_qs(parsed.query).get('cursor', [''])[0]
                if len(next_cursor) > 4096:
                    raise DiscoveryError('Source returned an oversized continuation cursor')
            more = bool(next_cursor)
            notice = 'Public Hub search includes base, fine-tuned, merged, adapter, and quantized repositories. Metadata may be incomplete.'
        else:
            # GitHub limits each search to an initial result window. Users can
            # narrow queries with official qualifiers rather than assuming full coverage.
            if (page - 1) * page_size >= 1000:
                raise ValueError('GitHub search window reached. Narrow the query to continue discovery.')
            query = q.strip() or ('topic:machine-learning' if kind == 'model' else 'topic:dataset')
            data, _ = self._json('https://api.github.com/search/repositories',
                                 {'q': query, 'sort': 'stars', 'order': 'desc', 'page': page, 'per_page': page_size})
            if not isinstance(data, dict) or not isinstance(data.get('items'), list) or len(data['items']) > page_size:
                raise DiscoveryError('Source returned an invalid discovery page')
            rows = data['items']
            more = page * page_size < min(_number(data.get('total_count')), 1000)
            next_cursor = ''
            notice = 'GitHub returns repositories, including tools and implementations. Review each source before configuring a runtime.'
            if data.get('incomplete_results'):
                notice += ' The source reported incomplete search results; narrow your query.'
            elif not more and page * page_size >= 1000:
                notice += ' Search window reached; narrow your query for other repositories.'
        return {'entries': [self._entry(source, kind, row) for row in rows], 'page': page,
                'page_size': page_size, 'next_cursor': next_cursor, 'has_more': more,
                'source': source, 'kind': kind, 'notice': notice}

    def add(self, source, identifier):
        if source not in {'huggingface', 'github'} or not ID.fullmatch(identifier) or len(identifier) > 200:
            raise ValueError('Use a canonical owner/name model identifier and a supported source')
        url = ('https://huggingface.co/api/models/' if source == 'huggingface' else 'https://api.github.com/repos/') + quote(identifier, safe='/')
        raw, _ = self._json(url)
        entry = self._entry(source, 'model', raw)
        if entry['id'].casefold() != identifier.casefold():
            raise DiscoveryError('Source repository identity did not match the requested model')
        rows = saved_models()
        rows = [r for r in rows if (r.get('source'), r.get('id', '').casefold()) != (source, identifier.casefold())]
        rows.append(entry)
        payload = json.dumps({'schema_version': 1, 'entries': rows}, indent=2, ensure_ascii=False) + '\n'
        if len(payload.encode('utf-8')) > 8 * LIMIT:
            raise ValueError('Saved model library budget reached. Remove unused references before adding more.')
        path = library_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.json', delete=False) as output:
                temporary = Path(output.name)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        return {'entry': entry, 'saved_to': str(path), 'notice': 'Saved source metadata to Zenith. Configure a compatible provider explicitly to use its weights.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    search = subs.add_parser('search', help='Search public source APIs on demand')
    search.add_argument('--source', choices=['huggingface', 'github'], default='huggingface')
    search.add_argument('--kind', choices=['model', 'dataset'], default='model')
    search.add_argument('--query', default='')
    search.add_argument('--page', type=int, default=1)
    search.add_argument('--page-size', type=int, default=20)
    search.add_argument('--cursor', default='')
    add = subs.add_parser('add', help='Save a model reference in the local library; no weight or code download')
    add.add_argument('--source', required=True, choices=['huggingface', 'github'])
    add.add_argument('--id', required=True, dest='identifier')
    subs.add_parser('list', help='List your saved model references offline')
    args = parser.parse_args(argv)
    try:
        service = Discovery()
        if args.command == 'list':
            result = {'entries': saved_models()}
        elif args.command == 'add':
            result = service.add(args.source, args.identifier)
        else:
            result = service.search(args.source, args.kind, args.query, args.page, args.page_size, args.cursor)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (DiscoveryError, ValueError, OSError) as exc:
        print(str(exc), file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
