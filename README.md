---
title: Zenith
emoji: ⚡
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
license: apache-2.0
---

# Zenith

**Talk to a small team of open language models, browse 1,000 model sources and 200 datasets, collect reviewed examples, and train your own adapter.** Zenith also includes an original small transformer you can train from random weights.

The original starter ZIP is preserved. Its Python project is now unpacked, extended, and runnable from this repository's root.

## Start chatting

Requires Python 3.10+ and internet for the first model download. No paid AI API key is needed. The default team uses [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) and [SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct) for drafting, cross-review, and final synthesis. Both are small CPU-capable models and have limited ability. Allow roughly 6–8 GB of available RAM, several GB for Python packages, and approximately 1.7 GB for these weights. For lower memory and latency, set `AI_PROVIDER=huggingface` to use Qwen alone (roughly 4–6 GB available RAM). First startup is slower while weights download.

```bash
git clone https://github.com/jamescartel982-creator/Zenith.git
cd Zenith
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- macOS / Linux: `source .venv/bin/activate`

Then:

```bash
pip install -e ".[local]"
python -m agent.server
```

Open **http://127.0.0.1:7860**. Or run `python -m agent.cli` for terminal chat. The default server binds to your computer only. The configured models load on your first message. The default team makes up to four sequential model calls per answer, so it is slower than one model. Once its files are cached, Hugging Face inference can run offline (`HF_HUB_OFFLINE=1`).

For a smaller CPU-only PyTorch installation on supported platforms, install PyTorch from its CPU index **before** the local dependencies:

```bash
pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[local]"
```

Copy `.env.example` to `.env` to customize the provider, model, context length, or output length. Environment variables override `.env`. Keep tokens in the ignored `.env` file.

## Choose more capability

| Option | Setting | Practical use |
| --- | --- | --- |
| Single-model CPU option | `HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct` | Basic chat and quick experiments |
| Larger local chat | `HF_MODEL=Qwen/Qwen2.5-1.5B-Instruct` | More capacity; more memory and latency |
| Stronger open chat | `HF_MODEL=Qwen/Qwen2.5-7B-Instruct` | GPU recommended; ~14 GB weights at float16 before runtime overhead |
| Quantized coding model | `AI_PROVIDER=ollama`, `OLLAMA_MODEL=qwen2.5-coder:7b` | Local code assistance through Ollama |
| Your own scratch model | `AI_PROVIDER=tiny` | Architecture and training experiments |

The listed Qwen Hugging Face checkpoints use Apache-2.0 licenses. Review the license for any replacement model. A larger model needs more compute; changing a name cannot make a laptop run a huge model cheaply. Direct Hugging Face inference uses float32 on CPU and float16 on accelerators. This implementation does not quantize direct HF loads. `ZENITH_DEVICE=auto` selects CUDA, Apple MPS, or CPU.

For [Ollama](https://github.com/ollama/ollama), install its runtime and pull your model:

```bash
ollama pull qwen2.5-coder:7b
pip install -e .
```

Put `AI_PROVIDER=ollama` in `.env`, then start Zenith normally. Ollama runs on `http://localhost:11434` by default. No PyTorch installation is needed for this provider.

## Model catalog, dataset sources, and collaboration

The bundled, source-backed catalog contains exactly:

| Source | Model references | Dataset sources |
| --- | ---: | ---: |
| Hugging Face | 500 | 100 |
| GitHub | 500 | 100 |
| **Total** | **1,000** | **200** |

Open **Browse catalog** in the chat UI to search, filter, and follow source links. Records include observed popularity, task, license metadata, timestamps, and provenance. Hugging Face selection uses downloads/likes with explicit practical CPU additions; GitHub selection ranks relevant candidates by stars after filtering. These are popularity-based selections, not a measured ranking of answer quality. GitHub entries are model implementations or dataset-source repositories, not ready-to-call chat endpoints. Many catalog models serve vision, audio, embeddings, or other tasks.

**Only the configured team runs.** The default two-model team shares its drafts, performs a cross-review, and synthesizes a final response. Each answer shows executed stages and any failure/fallback. To customize, copy `config/team.example.json` to an ignored local file and set `ZENITH_TEAM_CONFIG` to that path. Select up to three experts per request from a roster of at most 32, plus an optional reviewer and a synthesizer. The provider cache is bounded; the whole catalog is never loaded into memory.

Datasets are searchable source metadata until imported. Import selected text columns with `python -m scripts.import_dataset`; the local search index can then supply cited excerpts to all models participating in an answer. It does not train weights automatically or download all 200 datasets. See [team and dataset instructions](docs/model-team.md) for exact commands, limits, selection methods, and how to configure larger models.

```bash
python -m scripts.catalog --validate
python -m scripts.catalog --kind model --source huggingface --query Qwen
python -m scripts.catalog --kind dataset --source github
```

## How improvement works

1. Chat and open **Review this answer** beneath a response.
2. Rate it. For a poor answer, write the correct answer.
3. Check **Approve this answer and its context for training**, then save the review.
4. Export reviewed examples. Re-rating replaces the previous review; examples are not duplicated.
5. Fine-tune a candidate adapter, inspect its held-out results, and try it before adopting it.

A rating alone does not authorize training use. Approvals are local to this server. Changing your review or deleting a conversation removes it from future exports; existing exported datasets and trained weights are separate files.

```bash
python -m scripts.export_training_data
pip install -e ".[train]"
python -m scripts.train_lora --output-dir artifacts/zenith-v1
```

Collect at least five usable training examples and a separate held-out example across at least two independent conversations. Start new conversations for evaluation topics. Hundreds of diverse, accurate examples are more useful. The exporter keeps entire conversations and repeated user prompts in the same split and removes exact duplicates. This prevents a held-out answer leaking into a later training turn’s context. If every conversation is connected by repeated prompts, collect independent conversations to obtain an evaluation split. It preserves the actual multi-turn input used for inference. The trainer uses the base model's chat template, trains only the final assistant response, and excludes prompt and padding tokens from loss. Over-length examples are reported and skipped.

The output contains an adapter, tokenizer, and `training_report.json` with baseline and candidate evaluation loss, resolved base revision, dataset hashes, and run settings. Lower held-out loss is useful evidence, but does not establish general intelligence or better answers across tasks. Also compare normal chats and domain-specific checks. The bundled tiny smoke dataset used during development is only a plumbing check, not a capability benchmark.

Evaluate independently:

```bash
python -m scripts.evaluate --data data/eval.jsonl
python -m scripts.evaluate --data data/eval.jsonl --adapter artifacts/zenith-v1
```

To use your candidate, set `ZENITH_ADAPTER=artifacts/zenith-v1` in `.env`, keep `HF_MODEL` equal to its base model, and restart. To roll back, clear `ZENITH_ADAPTER`. Pin `HF_REVISION` to the base revision recorded in the training report for reproducibility.

The weights do **not** change during chat. Zenith does not execute generated code, rewrite its source, or claim it has performed actions from a conversation.

## Train Zenith's own transformer

`agent/tiny.py` implements a decoder-only transformer: UTF-8 byte tokens, causal multi-head attention, pre-norm residual blocks, feed-forward layers, learned positions, and tied embedding/output weights. It starts with random weights and trains with next-token cross-entropy. This is a working architecture and training loop, **not a pretrained capable LLM**.

```bash
python -m scripts.train_tiny --corpus path/to/your-text.txt --steps 1000 --output-dir artifacts/tiny
python -m scripts.sample_tiny --checkpoint artifacts/tiny/model.pt --prompt "User: Hello\nAssistant:"
```

Supply a sufficiently large UTF-8 corpus you have rights to use. The trainer reserves the final 10% of bytes for evaluation before sampling windows and records loss before/after training. By default it needs over 5,200 bytes to fit a 512-byte evaluation window. For experiments on a smaller corpus, reduce `--context-length`. The same checkpoint can serve chat using `AI_PROVIDER=tiny`; chat needs training text in `System: …`, `User: …`, `Assistant: …` form and a large enough context window. Short training runs will produce poor or meaningless output.

For useful conversation today, use the pretrained open model and fine-tuning workflow above. Training a broadly capable LLM from scratch requires far more data, compute, and evaluation than this small project supplies.

## Deploy

A non-root CPU Docker image, persistent Compose volumes, access-token support, and Hugging Face Docker Space metadata are included. See [deployment instructions](docs/deployment.md).

```bash
# Copy .env.example to .env and set ZENITH_API_TOKEN to a long random token.
# Generate one locally: python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up --build -d
```

Open http://127.0.0.1:7860, expand **Server access**, and enter your token. Docker requires at least 32 characters. Its default network binding is local; use HTTPS and a persistent disk when deploying to a public host.

## Project map

- `agent/server.py`, `agent/web/`: browser UI and authenticated chat/review API.
- `agent/providers.py`, `agent/ensemble.py`: direct inference and bounded model-team deliberation.
- `agent/registry.py`, `agent/catalog/`: 1,000 model references and 200 dataset sources.
- `scripts/import_dataset.py`: bounded text ingestion and source-linked local retrieval.
- `agent/core.py`, `agent/storage.py`: bounded generation and conversation-scoped SQLite storage.
- `agent/learning.py`, `scripts/`: reviewed export, LoRA training, evaluation, scratch training, and optional model upload.
- `tests/`: conversation isolation, approval/revocation, loss masks, API errors/authentication, and transformer checks.

## Tests and evidence

```bash
pip install -e ".[test]"
python -m unittest discover -s tests -v
```

Torch-specific checks skip if the optional local dependencies are absent. GitHub Actions runs both lightweight checks and a CPU transformer test job. See [validation notes](docs/validation.md) for checks actually run during development.

This is a single-owner assistant, not a multi-tenant service. The shared access token is not a user-account system. Database files contain conversation text. Model downloads follow the selected Hub revision, use safetensors, and disable remote custom code. Existing starter JSONL files are left untouched; import would need an explicit review because they have no isolated conversation IDs.

## Upstream software

Zenith's code is Apache-2.0, with the original repository license retained. Open weights and dependencies keep their own licenses; weights are downloaded rather than copied into Git. See [upstream references](docs/upstream.md). The original MIT model-card placeholder was replaced with a card appropriate to the default Apache-2.0 Qwen base.
