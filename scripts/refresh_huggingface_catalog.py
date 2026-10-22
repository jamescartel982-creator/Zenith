"""Refresh Zenith's metadata-only Hugging Face model and dataset catalogs.

Reads public repository metadata; never downloads weights, data rows, or remote code.
The bundled snapshot was collected through Firecrawl's Hugging Face provider, with
revision-only Hub API supplementation because the list provider omits commit SHAs.
This standalone refresher uses the same public Hub metadata API and selection rules.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
PRACTICAL = ('Qwen/Qwen2.5-0.5B-Instruct', 'HuggingFaceTB/SmolLM2-360M-Instruct')
RECOMMENDED = set(PRACTICAL) | {
    'Qwen/Qwen2.5-1.5B-Instruct', 'Qwen/Qwen2.5-7B-Instruct',
    'Qwen/Qwen2.5-Coder-7B-Instruct', 'Qwen/Qwen3-0.6B', 'Qwen/Qwen3-4B',
    'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B',
}
NATIVE_FAMILIES = {'qwen2', 'qwen3', 'llama', 'mistral', 'gemma', 'gemma2', 'phi', 'phi3'}
DATASET_EXCLUDE = re.compile(
    r'documentation-images|doc-build|imgbed|/frontend$|/results$|/requests$|'
    r'course-images|/bad_prompt$|/EasyNegative$|internship-warehouse|'
    r'flatpak|tokenizer|gallery|file_cache|/osworld_v2_assets|/parity-experiments|'
    r'/Submission-Archive|/Rosetta-Activations|sae-jailbreaks-cache', re.I)
# Some established collections omit task tags. These names are explicit exceptions,
# not inferred claims that arbitrary high-download repositories are training data.
UNTAGGED_DATASETS = {
    'Anthropic/hh-rlhf', 'OpenAssistant/oasst1', 'Rowan/hellaswag',
    'open-thoughts/OpenThoughts-114k', 'teknium/OpenHermes-2.5',
    'gaia-benchmark/GAIA', 'open-r1/OpenR1-Math-220k', 'HuggingFaceTB/cosmopedia',
    'HuggingFaceTB/smollm-corpus', 'meta-math/MetaMathQA', 'GAIR/lima',
    'cais/hle', 'nvidia/Llama-Nemotron-Post-Training-Dataset',
    'SWE-bench/SWE-bench_Verified', 'princeton-nlp/SWE-bench_Verified',
    'EleutherAI/hendrycks_math', 'nvidia/PhysicalAI-Autonomous-Vehicles',
    'allenai/objaverse', 'HuggingFaceM4/the_cauldron', 'HuggingFaceM4/FineVision',
    'mlfoundations/dclm-baseline-1.0', 'PleIAs/common_corpus', 'openai/gdpval',
    'anon8231489123/ShareGPT_Vicuna_unfiltered',
}
PERMISSIVE = {'apache-2.0', 'mit', 'bsd', 'bsd-3-clause', 'bsd-2-clause', 'cc0-1.0'}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def api_get(url, params=None):
    for attempt in range(3):
        response = requests.get(url, params=params, timeout=(10, 60),
                                headers={'User-Agent': 'ZenithCatalog/0.3 metadata-only'})
        if response.status_code in {429, 502, 503, 504} and attempt < 2:
            retry = response.headers.get('Retry-After', '2')
            delay = min(30, max(1, int(retry))) if retry.isdigit() else 2
            time.sleep(delay)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError('Hub metadata request failed')


def as_list(value):
    return value if isinstance(value, list) else [value] if value else []


def normalize_api_row(row, kind):
    card, tags = row.get('cardData') or {}, row.get('tags') or []
    declared = as_list(card.get('license')) or [tag.split(':', 1)[1] for tag in tags if tag.startswith('license:')]
    common = {
        **row, 'downloads_30d': row.get('downloads', 0),
        'license': declared[0] if declared else None, 'licenses': declared,
        'languages': as_list(card.get('language')),
        'last_modified': row.get('lastModified'),
    }
    if kind == 'models':
        common['base_models'] = as_list(card.get('base_model'))
    else:
        common['task_categories'] = as_list(card.get('task_categories')) or [tag.split(':', 1)[1] for tag in tags if tag.startswith('task_categories:')]
        common['formats'] = [tag.split(':', 1)[1] for tag in tags if tag.startswith('format:')]
        common['modalities'] = [tag.split(':', 1)[1] for tag in tags if tag.startswith('modality:')]
        common['size_categories'] = as_list(card.get('size_categories'))
    return common


def fetch_pages(kind, sort, count):
    fields = ['author', 'cardData', 'downloads', 'likes', 'gated', 'private', 'lastModified', 'sha', 'tags']
    fields += ['library_name', 'pipeline_tag'] if kind == 'models' else ['description']
    params = [('sort', sort), ('direction', '-1'), ('limit', '100')] + [('expand', field) for field in fields]
    pages, remaining, url = [], count, f'https://huggingface.co/api/{kind}'
    while remaining > 0:
        response = api_get(url, params)
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            break
        rows = rows[:remaining]
        pages.append({'source_url': response.url, 'observed_at': utc_now(),
                      'via': 'Hugging Face public Hub API',
                      'results': [normalize_api_row(row, kind) for row in rows]})
        remaining -= len(rows)
        url, params = response.links.get('next', {}).get('url'), None
        if not url:
            break
    return pages


def read_sources(directory):
    directory = Path(directory)
    model_pages = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(directory.glob('models_*.json'))]
    dataset_pages = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(directory.glob('datasets_*.json'))]
    practical = json.loads((directory / 'practical_models.json').read_text(encoding='utf-8'))
    model_pages.append(practical)
    for page in model_pages + dataset_pages:
        page['via'] = 'Firecrawl Hugging Face provider'
    revisions = {}
    for path in directory.glob('*revision*.json'):
        document = json.loads(path.read_text(encoding='utf-8'))
        for row in document['results']:
            revisions[row['id']] = (row.get('sha'), document['api_url'])
    for page in model_pages + dataset_pages:
        for row in page['results']:
            if row['id'] in revisions:
                row['sha'], row['revision_api_url'] = revisions[row['id']]
    return model_pages, dataset_pages


def observed(page):
    if page.get('observed_at'):
        return page['observed_at']
    milliseconds = page.get('observed_at_ms')
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat().replace('+00:00', 'Z') if milliseconds else utc_now()


def unique_rows(pages):
    rows = {}
    for page in pages:
        for row in page['results']:
            if row.get('private') or not row.get('id'):
                continue
            rows[row['id']] = {**row, '_source_url': page.get('source_url', 'https://huggingface.co/api/models'),
                               '_via': page.get('via', 'Hugging Face public Hub API'), '_observed_at': observed(page)}
    return list(rows.values())


def checkpoint_type(row):
    name, tags = row['id'].lower(), {str(tag).lower() for tag in row.get('tags', [])}
    if 'peft' in tags or 'lora' in tags or 'adapter' in tags:
        return 'adapter'
    if 'gguf' in tags or any(part in name for part in ('-gguf', '-gptq', '-awq', '-mlx', '-nvfp4', '-bnb-', '-fp8', '-int4')):
        return 'quantized'
    if row.get('library_name') == 'diffusion-single-file' or 'comfyui' in tags:
        return 'repackaged'
    return 'full'


def model_entry(row, rank, cutoff_rank, practical_addition=False):
    identifier, tags = row['id'], row.get('tags') or []
    task, library = row.get('pipeline_tag') or 'unknown', row.get('library_name') or 'unknown'
    kind = checkpoint_type(row)
    instruction = bool(re.search(r'instruct|chat|deepseek-r1|qwen3-(?:0\.6|1\.7|4|8|14|32)b$', identifier, re.I))
    native = bool(set(tags) & NATIVE_FAMILIES)
    chat = task == 'text-generation' and library == 'transformers' and kind == 'full' and instruction and native and not row.get('gated') and 'custom_code' not in tags
    declared = row.get('license') or 'unknown'
    support = 'huggingface' if chat else 'reference_only'
    roles = ['general', 'reviewer'] if chat else []
    if chat and re.search('coder|code', identifier, re.I):
        roles.append('coding')
    if chat and re.search('reason|deepseek-r1|qwen3', identifier, re.I):
        roles.append('reasoning')
    reason = 'Practical CPU council preset, added explicitly outside the popularity cutoff.' if practical_addition else 'High trailing-30-day Hub downloads among the public model candidate pool; likes retained as a secondary indicator.'
    return {
        'id': identifier, 'source': 'huggingface', 'kind': 'model', 'name': identifier.split('/')[-1],
        'url': f'https://huggingface.co/{identifier}',
        'description': f'{task} model repository by {row.get("author") or identifier.split("/")[0]}; library: {library}. Metadata catalog entry; weights are not installed.',
        'task': task, 'library': library, 'license': declared, 'licenses': row.get('licenses') or ([] if declared == 'unknown' else [declared]),
        'downloads': int(row.get('downloads_30d') or 0), 'likes': int(row.get('likes') or 0),
        'popularity_rank': rank, 'source_popularity_rank': cutoff_rank, 'observed_at': row['_observed_at'],
        'runtime_support': support, 'runtime_verified': False, 'installed': False,
        'chat_candidate': chat, 'checkpoint_type': kind, 'gated': bool(row.get('gated')),
        'revision': row.get('sha'), 'tags': tags[:18], 'roles': roles,
        'recommended': bool(identifier in RECOMMENDED and chat and declared in PERMISSIVE),
        'selection_reason': reason,
        'provenance': {'api_url': row['_source_url'], 'observed_at': row['_observed_at'], 'via': row['_via'],
                       **({'revision_api_url': row['revision_api_url']} if row.get('revision_api_url') else {})},
    }


def dataset_score(row):
    return math.log10(1 + int(row.get('downloads_30d') or 0)) + math.log10(1 + int(row.get('likes') or 0))


def dataset_entry(row, rank):
    tasks = [task for task in row.get('task_categories', []) if task != 'other']
    identifier = row['id']
    declared = row.get('license') or 'unknown'
    text = re.sub(r'\s+', ' ', row.get('description') or '').strip()[:700]
    return {
        'id': identifier, 'source': 'huggingface', 'kind': 'dataset', 'name': identifier.split('/')[-1],
        'url': f'https://huggingface.co/datasets/{identifier}',
        'description': text or 'Established dataset repository; inspect its dataset card and schema before use.',
        'task': tasks[0] if tasks else 'unspecified', 'task_categories': tasks,
        'license': declared, 'licenses': row.get('licenses') or ([] if declared == 'unknown' else [declared]),
        'downloads': int(row.get('downloads_30d') or 0), 'likes': int(row.get('likes') or 0),
        'popularity_rank': rank, 'popularity_score': round(dataset_score(row), 6),
        'observed_at': row['_observed_at'], 'runtime_support': 'reference_only',
        'runtime_verified': False, 'installed': False, 'training_approved': False,
        'gated': bool(row.get('gated')), 'revision': row.get('sha'), 'tags': (row.get('tags') or [])[:18],
        'languages': row.get('languages') or [], 'formats': row.get('formats') or [],
        'size_categories': row.get('size_categories') or [],
        'selection_reason': 'Task-tagged or explicitly recognized AI dataset, ranked by log10(1+30-day downloads)+log10(1+likes) after excluding assets and leaderboard logs.',
        'provenance': {'api_url': row['_source_url'], 'observed_at': row['_observed_at'], 'via': row['_via'],
                       **({'revision_api_url': row['revision_api_url']} if row.get('revision_api_url') else {})},
    }


def build_catalogs(model_pages, dataset_pages):
    rows = unique_rows(model_pages)
    rows = [row for row in rows if not re.search(r'internal-testing|tiny-random|/test[-_]', row['id'], re.I)]
    rows.sort(key=lambda row: (-int(row.get('downloads_30d') or 0), -int(row.get('likes') or 0), row['id']))
    ranks = {row['id']: index for index, row in enumerate(rows, 1)}
    selected = rows[:500]
    additions = []
    for identifier in PRACTICAL:
        if not any(row['id'] == identifier for row in selected):
            candidate = next((row for row in rows if row['id'] == identifier), None)
            if candidate is None:
                raise ValueError(f'Missing practical model metadata: {identifier}')
            # Preserve all previously inserted practical additions.
            replace = next(index for index in range(len(selected)-1, -1, -1) if selected[index]['id'] not in PRACTICAL)
            selected[replace] = candidate
            additions.append(identifier)
    selected.sort(key=lambda row: (-int(row.get('downloads_30d') or 0), -int(row.get('likes') or 0), row['id']))
    models = [model_entry(row, rank, ranks[row['id']], row['id'] in additions) for rank, row in enumerate(selected, 1)]
    data = unique_rows(dataset_pages)
    data = [row for row in data if not DATASET_EXCLUDE.search(row['id']) and
            (any(task != 'other' for task in row.get('task_categories') or []) or row['id'] in UNTAGGED_DATASETS)]
    data.sort(key=lambda row: (-dataset_score(row), -int(row.get('downloads_30d') or 0), row['id']))
    datasets = [dataset_entry(row, rank) for rank, row in enumerate(data[:100], 1)]
    if len(models) != 500 or len(datasets) != 100:
        raise ValueError(f'Insufficient real metadata: {len(models)} models, {len(datasets)} datasets')
    generated = utc_now()
    common = {'schema_version': 1, 'source': 'huggingface', 'generated_at': generated,
              'metadata_only': True, 'weights_or_data_downloaded': False,
              'license_note': 'Licenses are publisher-reported metadata, not a grant or legal review. Unknown means not declared.'}
    return (
        {**common, 'kind': 'model', 'selection': {'candidate_count': len(rows), 'method': '500 high-download public model repositories excluding internal-testing; explicit CPU council additions replace cutoff entries.', 'practical_additions': additions, 'popularity_is_not_quality': True, 'chat_candidate_note': 'Conservative native Transformers/text-generation metadata candidates only; installed package compatibility, chat template, memory, license and inference still require validation.'}, 'entries': models},
        {**common, 'kind': 'dataset', 'selection': {'candidate_count': len(unique_rows(dataset_pages)), 'eligible_count': len(data), 'method': 'Top 200 by downloads plus top 100 by likes; task/recognition and asset filters; rank by log10(1+downloads)+log10(1+likes).', 'popularity_is_not_quality': True, 'training_note': 'No dataset rows are downloaded or mixed into training; individual license, schema, quality, rights and split review are required.'}, 'entries': datasets},
    )


def validate_catalog(document, count, kind):
    rows = document['entries']
    if len(rows) != count or len({row['id'].casefold() for row in rows}) != count:
        raise ValueError('Catalog count or uniqueness mismatch')
    prefix = 'https://huggingface.co/' + ('datasets/' if kind == 'dataset' else '')
    for row in rows:
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', row['id']) or row['url'] != prefix + row['id']:
            raise ValueError(f'Invalid canonical Hub identity: {row["id"]}')
        if row['source'] != 'huggingface' or row['kind'] != kind or row['runtime_verified'] or row['installed']:
            raise ValueError('Invalid metadata-only status')
        datetime.fromisoformat(row['observed_at'].replace('Z', '+00:00'))
        if row.get('revision') and not re.fullmatch('[a-f0-9]{40}', row['revision']):
            raise ValueError('Invalid model/dataset revision')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'agent/catalog')
    parser.add_argument('--source-dir', type=Path, help='Optional cached provider snapshots, for reproducible build review')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.validate_only:
        for filename, count, kind in [('huggingface_models.json', 500, 'model'), ('huggingface_datasets.json', 100, 'dataset')]:
            validate_catalog(json.loads((args.output_dir / filename).read_text(encoding='utf-8')), count, kind)
        print('Validated 500 unique Hugging Face models and 100 unique datasets.')
        return
    if args.source_dir:
        model_pages, dataset_pages = read_sources(args.source_dir)
    else:
        model_pages = fetch_pages('models', 'downloads', 600)
        for identifier in PRACTICAL:
            response = api_get(f'https://huggingface.co/api/models/{identifier}')
            model_pages.append({'source_url': response.url, 'observed_at': utc_now(), 'results': [normalize_api_row(response.json(), 'models')]})
        dataset_pages = fetch_pages('datasets', 'downloads', 200) + fetch_pages('datasets', 'likes', 100)
    models, datasets = build_catalogs(model_pages, dataset_pages)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, document, count, kind in [('huggingface_models.json', models, 500, 'model'), ('huggingface_datasets.json', datasets, 100, 'dataset')]:
        validate_catalog(document, count, kind)
        path = args.output_dir / filename
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
        print(f'Wrote {len(document["entries"])} real {kind} entries to {path}')
    print(f'{sum(row["chat_candidate"] for row in models["entries"])} conservative metadata chat candidates; none marked installed or runtime verified.')


if __name__ == '__main__':
    main()
