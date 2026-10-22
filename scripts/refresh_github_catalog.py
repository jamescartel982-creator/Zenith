"""Refresh a metadata-only catalog of model and dataset repositories on GitHub.

Uses official public GitHub REST repository search; no repositories or payloads
are downloaded. Popularity is stars within the documented candidate searches,
not a claim of exhaustive global ranking or model quality.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

import requests

API = 'https://api.github.com/search/repositories'
COMMON = 'archived:false fork:false stars:>100'
MODEL_QUERIES = [
    ('text-generation', 'org:deepseek-ai'),
    ('text-generation', 'org:meta-llama'),
    ('text-generation', 'org:QwenLM'),
    ('text-generation', 'org:mistralai'),
    ('model-implementation', 'org:openai'),
    ('model-implementation', 'org:facebookresearch'),
    ('model-implementation', 'org:google-deepmind'),
    ('text-generation', 'topic:large-language-model'),
    ('text-generation', 'topic:llm'),
    ('text-generation', 'topic:language-model'),
    ('text-generation', 'topic:transformer'),
    ('image-generation', 'topic:diffusion-models'),
    ('image-generation', 'topic:text-to-image'),
    ('image-generation', 'topic:generative-adversarial-network'),
    ('computer-vision', 'topic:object-detection'),
    ('computer-vision', 'topic:semantic-segmentation'),
    ('computer-vision', 'model in:description topic:computer-vision'),
    ('audio', 'topic:speech-synthesis'),
    ('audio', 'topic:speech-recognition'),
    ('multimodal', 'topic:vision-language-model'),
    ('model-implementation', 'model in:description topic:pytorch'),
    ('model-implementation', '"official" "implementation" in:description'),
    ('model-implementation', '"pretrained" "model" in:description'),
    ('model-implementation', '"pre-trained" "model" in:description'),
    ('graph-learning', 'topic:graph-neural-networks'),
    ('computer-vision', '"pytorch implementation" in:description'),
    ('text-generation', '"language model" in:description'),
]
DATASET_QUERIES = [
    ('dataset', 'topic:dataset'),
    ('dataset', 'topic:datasets'),
    ('dataset', '"dataset" in:description stars:>1000'),
    ('dataset', '"corpus" in:name,description'),
    ('dataset', 'org:google-research-datasets'),
    ('dataset', 'org:allenai dataset'),
    ('dataset', 'org:bigcode-project'),
    ('dataset', 'org:bigscience-workshop'),
    ('dataset', 'org:openai'),
    ('dataset', 'dataset in:name topic:machine-learning'),
    ('dataset', 'dataset in:name topic:deep-learning'),
    ('dataset', 'dataset in:name topic:nlp'),
    ('dataset', 'dataset in:name topic:computer-vision'),
    ('dataset', '"dataset" "official" in:description'),
    ('dataset', '"dataset" "corpus" in:description'),
    ('dataset', '"dataset" "benchmark" in:description'),
    ('dataset', '"datasets" in:name'),
]
EXCLUDED_NAMES = {
    'transformers', 'diffusers', 'pytorch', 'pytorch-lightning', 'datasets',
    'comfyui', 'vllm', 'vllm-omni', 'llama.cpp', 'ollama', 'deepspeed',
    'tensorRT-llm'.lower(), 'accelerate', 'peft', 'trl', 'bitsandbytes',
    'wandb', 'netron', 'ludwig', 'inference', 'lmflow', 'llama-cookbook',
    'llama-factory', 'llamafactory', 'unsloth', 'autogpt', 'autogen',
    'langchain', 'langgraph', 'crewai', 'opencompass', 'kag', 'ragflow',
    'scrapegraph-ai', 'pocketflow', 'pocketflow-tutorial-codebase-knowledge',
    'rig', 'atomic-agents', 'bertviz', 'soup', 'notebooks', 'generative-ai',
    'docsGPT'.lower(), 'open-webui', 'text-generation-webui',
}
NEGATIVE_NAME = re.compile(r'awesome|survey|course|tutorial|cookbook|cheatsheet|interview|paper[-_]?list|roadmap|resources|prompt[-_]?engineering|jailbreak|collection|cheat[-_]?sheet', re.I)
MODEL_TOOL_NAME = re.compile(r'prompts|prompts?[-_.]|-app$|rag(?:[-_]|$)|system[_-]?prompt|for-beginners|agent|gpt4free|9router|copilot|chatchat|chatbot|webui|web-ui|drizzle|grad-cam|mcp|annotation|anylabel|from-scratch|hands-on|pytorch-cnn-visualizations|harness|metrics|playground|learn-|chatgpt-clone', re.I)
MODEL_TOOL_DESCRIPTION = re.compile(r'\bagents?\b|agentic|retrieval.augmented|\bRAG\b|workflow|\bGUI\b|\bplatform\b|\bapplication\b|\bapps?\b|\bvisualiz|\bMCP\b|command.line|AI assistant|knowledge.based|research assistant|system prompts|\blectures\b|\blessons\b|\bbook\b|frontend|annotation|packs your|censorship removal|model serving|serving for|llm providers|models? . providers|\bproviders\b|free ai coding|fine.tun.*yaml|everything is a plugin|management and startup tool|package for inference|usage of transformers', re.I)
MODEL_FRAMEWORK = re.compile(r'framework|toolkit|toolbox|\blibrary\b|speech recognition module|\btools\b|\bAPI\b|controlling large language models', re.I)
MODEL_IMPLEMENTATION = re.compile(r'pre.?trained|official (?:code|implementation)|implementation of|implementations of|model zoo|reference.*implementation|(?:is|are) (?:an? |the )?(?:open.weight |large |multimodal |language |generative |speech |bilingual |time.series |foundation )*model', re.I)
EXCLUDED_MODEL_IDS = {
    'janhq/jan', 'mudler/localai', 'ther1d/shell_gpt', 'simonw/llm',
    'p-e-w/heretic', 'roboflow/supervision', 'alexsjones/llmfit',
    'olafenwamoses/imageai', 'uberi/speech_recognition', 'dusty-nv/jetson-inference',
    'tiiny-ai/powerinfer', 'a-ghorbani/pocketpal-ai', 'unstructured-io/unstructured',
    'lutzroeder/netron', 'nvidia/tensorrt-llm', 'microsoft/lora',
    'ebony-vinyl/dsh-our-free-model', 'sudoskys/fastapi',
    'the-vibe-company/quivr', 'blakeblackshear/frigate',
    'zackriya-solutions/meetily', 'anil-matcha/open-generative-ai',
    'jushbjj/mr.-ranedeer-ai-tutor', 'rany2/edge-tts', 'voxel51/fiftyone',
    'wzmiaomiao/deep-learning-for-image-processing',
    'labmlai/annotated_deep_learning_paper_implementations',
    'deepseek-ai/deepseek-harness', 'expert-lsp/expert',
    'swe-bench/swe-bench', 'frgfm/torch-cam', 'roryclear/clearcam',
    'syhw/wer_are_we', 'abhineet123/deep-learning-for-tracking-and-detection',
    'rafaelpadilla/object-detection-metrics', 'saharmor/dalle-playground',
    'blaizzy/mlx-vlm', 'datawhalechina/learn-nlp-with-transformers',
    'josstorer/rwkv-runner', 'cartucho/map', 'nvidia/fastertransformer',
    'floneum/kalosm', 'kyegomez/tree-of-thoughts', 'xtekky/chatgpt-clone',
    'vhellendoorn/code-lms', 'bentrevett/pytorch-seq2seq',
    'raiyanyahya/how-to-train-your-gpt', 'graphdeeplearning/benchmarking-gnns',
}
NEGATIVE_DESCRIPTION = re.compile(r'(?:a |an |the )?(?:comprehensive |curated |extensible |modular |low-code |open-source )?(?:list of|list for|framework for|toolkit for|platform for|toolbox|visualizer|collection of tutorials)|web ?ui|inference engine|papers and resources|papers with code', re.I)
MODEL_SIGNAL = re.compile(r'model|neural|transformer|pytorch implementation|diffusion|synthesis|recognition|segmentation|detection|generative|gan\b|bert|llama|qwen|deepseek|mistral|gemma|attention|vision|tts|gpt', re.I)
DATASET_SIGNAL = re.compile(r'dataset|corpus|benchmark|annotations|training data|data set|data collection', re.I)
EXCLUDED_DATASET_IDS = {
    'fighting41love/funnlp', 'rom1504/img2dataset', 'financial-datasets/mcp-server',
    'datagouv/datagouv-mcp', 'graphdeco-inria/hierarchical-3d-gaussians',
    'binwang28/audio-ai-hub', 'adalca/medical-datasets', 'huggingface/dataset-viewer',
    'aisbench/benchmark', 'techascent/tech.ml.dataset', 'syncora-ai/syncora-benchmarks',
    'mlcommons/ck', 'roboflow/roboflow-python', 'nvidia/dataset_synthesizer',
    'yung-megafone/epstein-files', 'leobeeson/llm_benchmarks', 'maduc7/histopathology-datasets',
    'chaoswork/sft_datasets', 'webbreacher/whatsmyname',
    'ultralytics/assets', 'fix-macosx/yosemite-phone-home',
    'datasets/commons', 'waylon/ashare-quant-strategies',
    'sebastianruder/nlp-progress', 'pytorch/vision', 'cvat-ai/cvat',
    'conardli/easy-dataset', 'jindongwang/transferlearning', 'xerj-org/xerj',
    'nvidia/cosmos', 'dataelement/bisheng', 'simonw/datasette', 'voxel51/fiftyone',
    'redditsota/state-of-the-art-result-for-machine-learning-problems',
    'open-compass/opencompass', 'openlm-research/open_llama',
    'scikit-learn-contrib/imbalanced-learn', 'oarriaga/face_classification',
    'potree/potree', 'philackm/scrollablegraphview', 'kiln-ai/kiln',
    'argilla-io/argilla', 'csailvision/semantic-segmentation-pytorch',
    'minimaxir/textgenrnn', 'jazzband/tablib', 'cluebenchmark/cluedatasetsearch',
    'torchgeo/torchgeo', 'charmve/surface-defect-detection', 'opencsgs/csghub',
    'facebookresearch/sam-3d-body', 'datachain-ai/datachain',
    'zhulf0804/3d-pointcloud', 'cesiumgs/3d-tiles', 'itmeo/webgradients',
    'visual-layer/fastdup', 'stanford-oval/wikichat', 'capitalone/dataprofiler',
    'philipperemy/tensorflow-1.4-billion-password-analysis', 'refuel-ai/autolabel',
    'adaltas/node-csv', 'pydata/xarray', 'benfred/implicit',
    'larashero3-dotcom/lieflat-less-ai-tone', 'linhandev/dataset',
    'guillaume-chevalier/lstm-human-activity-recognition', 'roapi/roapi',
    'zjh-819/llmdatahub', 'trusted-ai/aif360', 'aaron-xichen/pytorch-playground',
    'rasterio/rasterio', 'abhineet123/deep-learning-for-tracking-and-detection',
    'ufoym/imbalanced-dataset-sampler', 'fudan-zvg/semantic-segment-anything',
    'eosphoros-ai/db-gpt-hub', 'smartflowai/emollm', 'saml ynnevans/transformer'.replace(' ', ''),
    'zhanlaoban/eda_nlp_for_chinese', 'openai/procgen', 'opencsgs/csghub-server',
    'thuml/large-time-series-model', 'ipea/geobr', 'iamaziz/pydataset',
    'mlcommons/croissant', 'robustbench/robustbench', 'farama-foundation/minari',
}
DATASET_NEGATIVE = re.compile(r'framework|library|toolkit|visualiz|data loader|dataloader|dataset generation tool|dataset annotation tool|list of|curated list|collection of datasets|public apis|\btool\b|\bplatform\b|\bframework\b|\bpackage\b|\bmodule\b|search engine|specification|dataset management|data processing|track the progress|\bparser\b|\bserver\b|corpus study|\bskill\b|\bindex\b|\bguide\b|dataset sampler|dataset.*format|format.*datasets|pytorch implementation|\bagents?\b|papers and datasets|papers, codes|papers.*tutorials', re.I)


def eligible(repo, kind):
    if repo.get('archived') or repo.get('fork') or repo.get('disabled'):
        return False
    name = repo['name']
    description = repo.get('description') or ''
    text = name + ' ' + description
    if NEGATIVE_NAME.search(name):
        return False
    if kind == 'model':
        return (repo['full_name'].lower() not in EXCLUDED_MODEL_IDS
                and not MODEL_TOOL_NAME.search(name)
                and not MODEL_TOOL_DESCRIPTION.search(description)
                and (not MODEL_FRAMEWORK.search(description) or MODEL_IMPLEMENTATION.search(description))
                and name.lower() not in EXCLUDED_NAMES and MODEL_SIGNAL.search(text)
                and not NEGATIVE_DESCRIPTION.search(description)
                and not re.search(r'^awesome|\bdatasets?\b', name, re.I))
    return bool(repo['full_name'].lower() not in EXCLUDED_DATASET_IDS
                and not re.search(r'mcp|tool|viewer|synthesizer|annotation|compiler', name, re.I)
                and DATASET_SIGNAL.search(text) and not DATASET_NEGATIVE.search(description)
                and name.lower() not in {'datasets', 'huggingface_hub', 'tensorflow_datasets'})


def fetch(session, query, page, cache_dir, refresh=False):
    params = {'q': query, 'sort': 'stars', 'order': 'desc', 'per_page': 100, 'page': page}
    key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:20]
    cached = cache_dir / f'{key}.json'
    if cached.exists() and not refresh:
        payload = json.loads(cached.read_text(encoding='utf-8'))
        return payload['data'], payload['observed_at'], payload['url']
    for attempt in range(4):
        response = session.get(API, params=params, timeout=(10, 60))
        if response.status_code in {403, 429} and attempt < 3:
            try:
                delay = float(response.headers.get('Retry-After') or max(1, int(response.headers.get('X-RateLimit-Reset', '0')) - time.time() + 1))
            except (TypeError, ValueError):
                delay = 10
            if delay > 60:
                raise RuntimeError('GitHub rate limit requires a wait over 60 seconds; retry later using the saved cache')
            print(f'GitHub rate limit: waiting {delay:.0f}s', flush=True)
            time.sleep(max(1, delay))
            continue
        response.raise_for_status()
        data = response.json()
        if data.get('incomplete_results'):
            raise RuntimeError(f'GitHub returned incomplete results for {query!r}; retry refresh later')
        observed = datetime.now(timezone.utc).isoformat()
        cached.write_text(json.dumps({'url': response.url, 'observed_at': observed, 'data': data}), encoding='utf-8')
        return data, observed, response.url
    raise RuntimeError('GitHub repository search rate limit did not clear')


def infer_task(repo, fallback, kind):
    if kind == 'dataset':
        return 'dataset'
    text = (' '.join(repo.get('topics') or []) + ' ' + repo['full_name'] + ' ' + (repo.get('description') or '')).lower()
    if re.search(r'text.to.speech|speech.synthesis|\btts\b|chattts|voxcpm|tacotron|fish.speech|bark|vits|emotivoice', text):
        return 'text-to-speech'
    if re.search(r'speech.recognition|speech.to.text|\basr\b|whisper|sensevoice|fireredasr', text):
        return 'automatic-speech-recognition'
    if re.search(r'source.separation|spleeter|audiosep|musicgen|audiogen|audio generation', text):
        return 'audio-generation-or-separation'
    if re.search(r'speech.enhancement|speech.processing|audio.*autoencoder|\brave\b', text):
        return 'audio-processing'
    if re.search(r'time.series|forecasting|timesfm|chronos', text):
        return 'time-series'
    if re.search(r'ocr|document.*parsing', text):
        return 'image-to-text'
    if re.search(r'vision.language|visual.language|multimodal|multi.modal|llava|internvl|qwen.*-vl|clip\b|moondream', text):
        return 'multimodal'
    if re.search(r'video.generation|video.to.video|text.to.video|animatediff|vid2vid', text):
        return 'video-generation'
    if re.search(r'object.detection|yolo|groundingdino|rf.detr', text):
        return 'object-detection'
    if re.search(r'segmentation|segment.anything|mask.rcnn|semantic.sam|unet|u.net|sam2', text):
        return 'image-segmentation'
    if re.search(r'diffusion|generative.adversarial|\bgan\b|stylegan|pix2pix|image.to.image|text.to.image|imagen|dall.e', text):
        return 'image-generation'
    if re.search(r'image.restoration|image.inpainting|deblurring|super.resolution|denoising|image.processing', text):
        return 'computer-vision'
    if re.search(r'language.model|large.language|llm|gpt|llama|qwen|deepseek|mistral|rwkv|chatglm', text):
        return 'text-generation'
    if re.search(r'reinforcement.learning|imitation.learning|reward.learning|probabilistic.modelling|probabilistic.modeling', text):
        return 'reinforcement-or-probabilistic-learning'
    if re.search(r'graph.neural|graph.learning|gcn|graphsage|graph.attention', text):
        return 'graph-learning'
    if re.search(r'language.model|large.language|llm|gpt|llama|qwen|deepseek|mistral|rwkv|chatglm', text):
        return 'text-generation'
    if re.search(r'computer.vision|classification|resnet|efficientnet|dinov', text):
        return 'computer-vision'
    return fallback

def gather(session, queries, kind, target, cache_dir, pages=1, refresh=False):
    pool = {}
    audit = []
    for task, query in queries:
        query = f'{query} {COMMON}'
        for page in range(1, pages + 1):
            data, observed, url = fetch(session, query, page, cache_dir, refresh)
            audit.append({'query': query, 'page': page, 'url': url, 'total_count': data['total_count'],
                          'returned_count': len(data['items']), 'observed_at': observed})
            for repo in data['items']:
                if not eligible(repo, kind):
                    continue
                key = repo['full_name'].lower()
                if key not in pool:
                    pool[key] = {'repo': repo, 'task': task, 'provenance': [], 'observed_at': observed}
                pool[key]['provenance'].append(url)
            print(f'{kind}: query={query!r} page={page} eligible_unique={len(pool)}', flush=True)
            if len(data['items']) < 100:
                break
    ranked = sorted(pool.values(), key=lambda item: (-item['repo']['stargazers_count'], item['repo']['full_name'].lower()))
    if len(ranked) < target:
        raise RuntimeError(f'Only {len(ranked)} eligible {kind} repositories; need {target}. Increase --pages or broaden documented queries.')
    entries = []
    for rank, item in enumerate(ranked[:target], 1):
        repo = item['repo']
        license_info = repo.get('license') or {}
        license_name = license_info.get('spdx_id') or 'unknown'
        if license_name == 'NOASSERTION':
            license_name = 'unknown'
        entries.append({
            'id': repo['full_name'], 'source': 'github', 'kind': kind,
            'name': repo['name'], 'url': repo['html_url'], 'description': repo.get('description') or '',
            'task': infer_task(repo, item['task'], kind), 'license': license_name, 'stars': repo['stargazers_count'],
            'forks': repo['forks_count'], 'popularity_rank': rank, 'observed_at': item['observed_at'],
            'pushed_at': repo.get('pushed_at'), 'runtime_support': 'reference_only',
            'runtime_verified': False, 'tags': repo.get('topics') or [],
            'language': repo.get('language'), 'default_branch': repo.get('default_branch'),
            'provenance': item['provenance'],
            'selection_reason': 'High star count among non-archived, non-fork repositories matching documented AI-model searches; heuristic relevance filter.' if kind == 'model' else 'High star count among non-archived, non-fork repositories matching documented dataset-source searches; heuristic relevance filter.',
            'artifact_type': 'model_implementation_repository' if kind == 'model' else 'dataset_source_repository',
            'usage_note': 'Reference metadata only. Repository code, weights, compatibility, model licenses and hardware must be reviewed before execution.' if kind == 'model' else 'Reference metadata only. Dataset files, access terms, provenance and suitability need review before ingestion or training.',
        })
    generated = datetime.now(timezone.utc).isoformat()
    return {'schema_version': 1, 'source': 'github', 'kind': kind, 'generated_at': generated,
            'selection': {'method': 'Union of official REST repository searches, heuristic relevance filtering, deduplication by case-insensitive owner/repo, then descending star count within that candidate pool.',
                          'global_top_claim': False, 'quality_benchmark_claim': False,
                          'candidates_after_filter': len(pool), 'count': target, 'queries': audit,
                          'limitations': ['Repository popularity is not model quality.', 'Metadata heuristics do not prove every repository is a standalone pretrained model.', 'Repository licenses may differ from weight/data licenses.', 'No weights, repositories or dataset contents are bundled or executed.']},
            'entries': entries}


def validate(catalog, expected):
    entries = catalog['entries']
    assert len(entries) == expected
    assert len({row['id'].lower() for row in entries}) == expected
    assert all(row['source'] == 'github' and row['runtime_support'] == 'reference_only' for row in entries)
    assert all(row['url'] == 'https://github.com/' + row['id'] for row in entries)
    assert [row['stars'] for row in entries] == sorted((row['stars'] for row in entries), reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('agent/catalog'))
    parser.add_argument('--cache-dir', type=Path, default=Path('data/catalog-cache/github'))
    parser.add_argument('--models', type=int, default=500)
    parser.add_argument('--datasets', type=int, default=100)
    parser.add_argument('--pages', type=int, default=1, help='Pages per documented query, at most 10')
    parser.add_argument('--refresh', action='store_true', help='Ignore cached source responses')
    args = parser.parse_args()
    if args.models < 1 or args.datasets < 1 or not 1 <= args.pages <= 10:
        parser.error('Positive counts and 1–10 pages are required')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                            'User-Agent': 'Zenith-Catalog/0.3'})
    token = os.getenv('GITHUB_TOKEN')
    if token:
        session.headers['Authorization'] = 'Bearer ' + token
    for kind, queries, count in [('model', MODEL_QUERIES, args.models), ('dataset', DATASET_QUERIES, args.datasets)]:
        catalog = gather(session, queries, kind, count, args.cache_dir, args.pages, args.refresh)
        validate(catalog, count)
        destination = args.output_dir / f'github_{kind}s.json'
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(destination)
        print(f'Wrote {count} {kind} entries to {destination}', flush=True)


if __name__ == '__main__':
    main()
