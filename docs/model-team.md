# Model catalog and team

Zenith contains 1,000 model references and 200 dataset sources: 500 models and 100 datasets each from Hugging Face and GitHub. The four snapshots live in `agent/catalog/` and are included in wheels and Docker images. Source timestamps, reported licenses, popularity, task metadata, and acquisition provenance are retained.

## Selection and meaning

Hugging Face models come from a high-download public candidate pool, excluding internal test checkpoints. The small SmolLM2 reviewer is an explicit practical addition outside the popularity cutoff. Downloads are trailing-30-day Hub counts; likes are also recorded. Dataset selection combines high-download/high-like candidates, filters documentation/assets, and ranks useful task-tagged or recognized collections by `log10(1+downloads)+log10(1+likes)`.

GitHub uses documented official repository-search queries, excludes forks/archived repositories and common tools/frameworks/indexes, then sorts the deduplicated relevant candidate pool by stars. This is not an exhaustive global top-500 claim. Repository metadata heuristics and spot checks do not establish model quality or guarantee every repository is a standalone pretrained checkpoint. Some entries provide multiple model implementations. Dataset sources may contain loaders, manifests, or links to externally hosted data rather than the complete payload in Git.

The snapshots include text, vision, audio, embedding, and other tasks. A vision model cannot be plugged into the text-chat provider merely because it is popular. GitHub repositories remain `reference_only`; use their official documentation to identify a supported checkpoint/runtime. Hub `chat_candidate` and `runtime_support` fields are conservative metadata assessments, not installation or compatibility guarantees. Live loaded-state comes from the configured runtime, independently of the immutable catalog.

Licenses are publisher-reported metadata, not a grant for every artifact in a repository. A repository license can differ from its weights/data terms. Unknown licenses are kept visibly unknown. No full repository, model weights, or dataset rows are copied into the catalog or silently mixed into training.

## Real collaboration

The default `AI_PROVIDER=ensemble` team runs:

1. Qwen2.5-0.5B-Instruct drafts an answer.
2. SmolLM2-360M-Instruct drafts independently.
3. SmolLM2 sees both drafts and proposes corrections.
4. Qwen sees the drafts/review and synthesizes a final answer to the original question.

The final answer includes a trace of the calls that actually ran, plus retrieved sources when present. Draft/review text is treated as untrusted candidate material. If a member fails, successful drafts remain available. If synthesis fails or the soft deadline prevents it, the response is labeled as a draft fallback. All-draft failure returns a model-unavailable error.

This is genuine communication between a configured small team, not execution of all 1,000 catalog entries. More models and model agreement do not guarantee a correct or improved answer. Compare results on representative held-out tasks before choosing a team. The two small defaults establish a runnable CPU workflow, not state-of-the-art quality.

## Configure your team

Copy `config/team.example.json` to `config/team.local.json`, edit it, and set:

```env
AI_PROVIDER=ensemble
ZENITH_TEAM_CONFIG=config/team.local.json
```

The example pins the primary Qwen revision. Pin other model revisions for reproducibility. Each member has an ID, display name, provider (`huggingface` or `ollama`), model, and role (`general`, `coding`, `math`, `reasoning`, or `critic`). Optional fields: revision, device, local adapter, and Ollama `base_url` without embedded credentials. The roster is trusted local configuration and cannot be modified by prompts or catalog clicks.

A larger hardware-backed roster could assign a Qwen coding model to `coding`, a separate math model to `math`, and a stronger general model as the synthesizer. Download/serve and validate those models first. For Ollama, run `ollama pull <model>` and set the member's provider/model/base URL. For HF, install `.[local]` and use a supported instruction checkpoint with a chat template and safetensors; arbitrary remote Python code remains disabled.

Limits:

- 2–32 configured members; keyword routing selects 1–3 drafting experts.
- Optional cross-review plus one synthesis call; no unlimited debate loop.
- `max_parallel=1`: sequential calls avoid retaining abandoned Torch threads.
- `max_cached_models=1..5`: LRU cache bounds retained providers; lowering it can require model reloads. Default 2 fits the default roster. Memory also depends on chosen weights, contexts, Torch allocation, and hardware.
- `max_proposal_chars` bounds draft/review material passed between stages.
- `round_timeout_seconds` is a **soft deadline checked between calls**. An in-progress local load/generation cannot safely be killed, and may overrun it. Ollama has its own network timeout. Later stages are skipped after the deadline.

English keyword routing is transparent and deterministic, not a trained quality predictor. For multilingual/general requests it falls back to general roster order. Keep the existing single-model mode (`AI_PROVIDER=huggingface` or `ollama`) when latency or memory matters more than deliberation.

## Import selected dataset text

The 200 sources become searchable references immediately. Their contents become answer context only after explicit import. Start with a small, relevant subset; automatically loading all collections would include enormous, gated, non-text, or incompatible data.

```bash
pip install -e ".[data]"
python -m scripts.catalog --kind dataset --source huggingface --query squad
python -m scripts.import_dataset --source huggingface --id rajpurkar/squad --revision main --split train --text-field context --limit 20
```

Use the exact revision from the catalog instead of `main` to pin the import. Specify `--subset` when the dataset requires a configuration. HF loading streams rows with remote dataset Python code disabled. Some source formats need extra dependencies or granted Hub access; unsupported/gated sources are not silently replaced.

For a GitHub dataset, select an exact public data file and a commit revision:

```bash
python -m scripts.import_dataset --source github --id lukes/ISO-3166-Countries-with-Regional-Codes --revision 145f1ad3caff212ed25f42b0ee2c8b92a75af895 --path all/all.csv --text-field name --limit 20
```

That example imports a bounded country-name column from a pinned CSV snapshot. For JSON imports, the file must be an array of row objects containing the selected text field. Nested JSON schemas need a local conversion first. CSV, JSONL/NDJSON, array JSON, text, and Markdown are supported; arbitrary code and archives are not executed. GitHub files have a 20 MiB limit. Imports examine at most 10,000 rows, retain at most 12,000 text characters per row in bounded chunks, and deduplicate repeated source/text pairs.

Imported documents are stored in the same local SQLite database, separately from conversation training approvals. Full-text search supplies up to five excerpts (default three, each at most 600 characters) with source URLs. They enter each participating model's input as untrusted evidence. This is lexical retrieval, not an embedding index or proof that a passage is reliable. `ZENITH_KNOWLEDGE_LIMIT=0` disables it. Importing does not update model weights.

The Docker image includes these import utilities. For a running Compose service, prefix the import command with `docker compose exec zenith` (for example, `docker compose exec zenith python -m scripts.import_dataset ...`). Its default data directory is the persistent `/app/data` volume.

Inspect `GET /api/knowledge` for counts. To remove an imported source locally:

```python
from agent.storage import Store
Store("data").delete_source("SOURCE_ID_PRINTED_BY_IMPORT")
```

Deleting a conversation does not remove independently imported knowledge. Approved training exports contain the exact generation context, which may include retrieved excerpts and ensemble proposals; review the full example before training or publishing.

## Refresh and validate

```bash
python -m scripts.refresh_huggingface_catalog
python -m scripts.refresh_github_catalog
python -m scripts.catalog --validate
```

Refresh commands read public source metadata only and fail if they cannot obtain real entries at the requested counts. They do not pad with invented IDs. GitHub responses are cached in ignored local data and respect API rate limits; optional `GITHUB_TOKEN` can be supplied through the environment. Do not commit credentials. Restart the server after replacing snapshots so its cached catalog reloads.

The browser Catalog supports source/type filters, search, pages, license/popularity details, and source links. It labels configured HF chat members separately and does not offer an unsafe “run any repository” button.
