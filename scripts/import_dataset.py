"""Import bounded text rows from a selected catalog dataset for local retrieval.

No training, model activation, or remote Python execution occurs during import.
"""
import argparse
import csv
import io
import json
from itertools import islice
from pathlib import Path, PurePosixPath
from urllib.parse import quote
import requests
from agent.config import Settings
from agent.registry import Catalog
from agent.storage import Store

MAX_GITHUB_BYTES = 20 * 1024 * 1024


def github_rows(repository, path, revision, text_field):
    parts = PurePosixPath(path)
    if parts.is_absolute() or '..' in parts.parts or not path or any(c in path for c in ('?', '#', '\\')):
        raise ValueError('Choose a repository-relative CSV, JSONL, JSON or text data file')
    if not revision or any(c in revision for c in ('?', '#', '\\')):
        raise ValueError('Choose an explicit GitHub data revision')
    url = f'https://raw.githubusercontent.com/{repository}/{quote(revision, safe="")}/{quote(path, safe="/")}'
    with requests.get(url, stream=True, timeout=(10, 60)) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_content(65536):
            content.extend(chunk)
            if len(content) > MAX_GITHUB_BYTES:
                raise ValueError('Data file exceeds 20 MiB import limit; select a smaller shard')
    text = content.decode('utf-8-sig')
    suffix = parts.suffix.lower()
    if suffix == '.csv':
        yield from csv.DictReader(io.StringIO(text))
    elif suffix in {'.jsonl', '.ndjson'}:
        for line in text.splitlines():
            if line.strip():
                yield json.loads(line)
    elif suffix == '.json':
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError('JSON data file must be an array of row objects')
        yield from rows
    elif suffix in {'.txt', '.md'}:
        for paragraph in text.split('\n\n'):
            if paragraph.strip():
                yield {text_field: paragraph}
    else:
        raise ValueError('Only CSV, JSONL, JSON, TXT and Markdown data files are supported')


def ingest(store, rows, source_id, url, text_field, limit):
    count = 0
    seen = 0
    for row in islice(rows, limit):
        seen += 1
        text = row.get(text_field) if isinstance(row, dict) else None
        if not isinstance(text, str) or not text.strip():
            continue
        # Bound both storage and the number of chunks derived from any one row.
        for start in range(0, min(len(text), 12000), 2000):
            if store.add_document(source_id, url, text[start:start + 2000]):
                count += 1
    return {'rows_examined': seen, 'documents_added': count, **store.knowledge_stats()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['huggingface', 'github'], required=True)
    parser.add_argument('--id', required=True, help='Dataset catalog owner/repository')
    parser.add_argument('--text-field', required=True, help='Text column to import')
    parser.add_argument('--limit', type=int, default=100, help='Maximum rows examined, 1–10000')
    parser.add_argument('--split', default='train')
    parser.add_argument('--subset', default=None)
    parser.add_argument('--revision', default=None, help='Pin a Hub/GitHub revision')
    parser.add_argument('--path', default=None, help='Required for GitHub: exact data file path')
    parser.add_argument('--data-dir', default=Settings().data_dir)
    parser.add_argument('--catalog-dir', default=None)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error('--limit must be 1–10000')
    entry = Catalog(args.catalog_dir).get(args.source, 'dataset', args.id)
    revision = args.revision or entry.get('revision')
    if args.source == 'huggingface':
        if not revision:
            parser.error('Dataset needs an explicit --revision for reproducible import')
        from datasets import load_dataset
        rows = load_dataset(args.id, name=args.subset, split=args.split, revision=revision,
                            streaming=True, trust_remote_code=False)
        url = entry['url'] + '/tree/' + quote(revision, safe='')
    else:
        if not args.path or not revision:
            parser.error('GitHub import needs --path and an explicit --revision commit SHA')
        rows = github_rows(args.id, args.path, revision, args.text_field)
        url = entry['url'] + '/blob/' + quote(revision, safe='') + '/' + quote(args.path, safe='/')
    source_id = f'{args.source}:{args.id}@{revision}' + (f'/{args.path}' if args.path else f'/{args.subset or "default"}/{args.split}')
    result = ingest(Store(args.data_dir), rows, source_id, url, args.text_field, args.limit)
    print(json.dumps({'source_id': source_id, 'url': url, 'catalog_license': entry.get('license', 'unknown'), **result}, indent=2))
    print('Imported text is available for cited local retrieval. Model weights were not changed.')


if __name__ == '__main__':
    main()
