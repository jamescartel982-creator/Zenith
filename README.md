---
title: Zenith
emoji: ⚡
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
license: apache-2.0
---

![Zenith — Open Intelligence, with an original anime-inspired guardian and a violet neural-energy sphere.](assets/zenith-banner.png)

# Zenith

**Talk to a small team of open language models, browse 1,000 model sources and 200 datasets, collect reviewed examples, and train your own adapter.** Zenith also includes an original small transformer you can train from random weights.

The original starter ZIP is preserved. Its Python project is now unpacked, extended, and runnable from this repository's root.

## Install locally: Windows or Linux

Python **3.10 or newer** is required; **Python 3.12 is recommended**. Internet is needed for package installation and the first model download. The installer creates a private `.venv`, installs CPU PyTorch when needed, saves user settings, and runs diagnostics. It preserves existing settings and conversations during upgrades.

The upgrades from [PR #1](https://github.com/jamescartel982-creator/Zenith/pull/1) are merged into `main`. These commands install the current version. You can also download `main` as a ZIP and extract it if Git is unavailable.

### Windows — PowerShell

Install Python from python.org or with `winget install -e --id Python.Python.3.12`, then reopen your terminal. From the folder where you want Zenith:

```powershell
git clone https://github.com/jamescartel982-creator/Zenith.git
cd Zenith
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --mode local
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 chat
```

For browser chat:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 serve
```

`ExecutionPolicy Bypass` applies to that PowerShell process; the installer does not change your system policy. The installed command also works directly: `& ".\.venv\Scripts\zenith.exe" doctor`.

### Linux — terminal

Install Python and its venv support first if necessary (Debian/Ubuntu: `sudo apt install python3 python3-venv git`). Then:

```bash
git clone https://github.com/jamescartel982-creator/Zenith.git
cd Zenith
bash install.sh --mode local
./run.sh chat
```

For browser chat:

```bash
./run.sh serve
```

Open **http://127.0.0.1:7860** after starting the server. The wrappers use the installed virtual environment without activation. You can also invoke `.venv/bin/zenith` on Linux or `.venv/Scripts/zenith.exe` on Windows directly from any working directory using its absolute path.

### Select a mode

| Installer flag | Behavior | Practical requirements |
| --- | --- | --- |
| `--mode local` | One Qwen2.5-0.5B instruction model; recommended first install | CPU; roughly 4–6 GB available RAM and ~1 GB weights |
| `--mode ensemble` | Qwen + SmolLM2 drafts, cross-review, and synthesis | Roughly 6–8 GB available RAM and ~1.7 GB weights; slower answers |
| `--mode ollama` | Lightweight Zenith client for an existing Ollama server | Install/start Ollama and pull its configured model separately |

Append `--download` to a local/ensemble install to cache configured weights during setup. Otherwise, the first message downloads them. Re-running the installer upgrades the application while preserving your profile. Use `--overwrite-config` only when you intend to replace the saved profile; environment variables and a checkout `.env` still take precedence. See [local installation and upgrade instructions](docs/local-installation.md).

### Useful terminal commands

After installation, use the platform wrapper (or the installed `zenith` executable):

```text
zenith chat                    Terminal conversation
zenith serve                   Browser chat on localhost
zenith doctor                  Dependency, storage, and cache checks
zenith models download         Cache configured HF model weights
zenith doctor --inference      Test a real response using cached weights
zenith catalog --validate      Check the 1,000-model / 200-dataset catalog
zenith --help                  List all available commands
```

The saved profile and conversations live in `%LOCALAPPDATA%\Zenith` on Windows and `~/.local/share/zenith` on Linux (or `XDG_DATA_HOME/zenith`). `ZENITH_HOME` selects another absolute location. Existing checkout `data/zenith.sqlite3` databases are retained. No paid AI API key is needed; model downloads use open checkpoints. Once cached, `HF_HUB_OFFLINE=1` makes supported HF loads use local files only.

## Choose more capability

The advanced `python`/`pip` examples below assume the installed environment is activated: Linux `source .venv/bin/activate`; PowerShell `. .\.venv\Scripts\Activate.ps1` (subject to your local execution policy). You can instead use `.venv/bin/python` or `.venv/Scripts/python.exe` directly, and invoke pip with that interpreter's `-m pip`. Normal chat and browser commands above need no activation.

| Option | Setting | Practical use |
| --- | --- | --- |
| Single-model CPU option | `AI_PROVIDER=huggingface`, `HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct` | Basic chat and quick experiments |
| Larger local chat | `HF_MODEL=Qwen/Qwen2.5-1.5B-Instruct` | More capacity; more memory and latency |
| Stronger open chat | `HF_MODEL=Qwen/Qwen2.5-7B-Instruct` | GPU recommended; ~14 GB weights at float16 before runtime overhead |
| Quantized coding model | `AI_PROVIDER=ollama`, `OLLAMA_MODEL=qwen2.5-coder:7b` | Local code assistance through Ollama |
| Your own scratch model | `AI_PROVIDER=tiny` | Architecture and training experiments |

The listed Qwen Hugging Face checkpoints use Apache-2.0 licenses. Review the license for any replacement model. A larger model needs more compute; changing a name cannot make a laptop run a huge model cheaply. Direct Hugging Face inference uses float32 on CPU and float16 on accelerators. This implementation does not quantize direct HF loads. `ZENITH_DEVICE=auto` selects CUDA, Apple MPS, or CPU.

When changing `HF_MODEL`, also set `HF_REVISION` to that model's commit or `main`; the installer's saved revision is pinned to the default small Qwen checkpoint.

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

**Only the configured team runs.** Ensemble mode uses a two-model team that shares its drafts, performs a cross-review, and synthesizes a final response. Each answer shows executed stages and any failure/fallback. To customize, copy `config/team.example.json` to an ignored local file and set `ZENITH_TEAM_CONFIG` to that path. Select up to three experts per request from a roster of at most 32, plus an optional reviewer and a synthesizer. The provider cache is bounded; the whole catalog is never loaded into memory.

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
python -m scripts.evaluate
python -m scripts.evaluate --adapter artifacts/zenith-v1
```

To use your candidate, set `ZENITH_ADAPTER=artifacts/zenith-v1` in `.env`, keep `HF_MODEL` equal to its base model, and restart. To roll back, clear `ZENITH_ADAPTER`. Pin `HF_REVISION` to the base revision recorded in the training report for reproducibility.

The weights do **not** change during chat. Zenith does not execute generated code, rewrite its source, or claim it has performed actions from a conversation.

## Train Zenith's own transformer

`agent/tiny.py` implements a decoder-only transformer: UTF-8 byte tokens, causal multi-head attention, pre-norm residual blocks, feed-forward layers, learned positions, and tied embedding/output weights. It starts with random weights and trains with next-token cross-entropy. This is a working architecture and training loop, **not a pretrained capable LLM**.

```bash
python -m scripts.train_tiny --corpus path/to/your-text.txt --steps 1000 --output-dir artifacts/tiny
python -m scripts.sample_tiny --checkpoint artifacts/tiny/model.pt --prompt "User: Hello\nAssistant:"
```

Supply a sufficiently large UTF-8 corpus you have rights to use. The trainer reserves the final 10% of bytes for evaluation before sampling windows and records loss before/after training. By default it needs over 5,200 bytes to fit a 512-byte evaluation window. For experiments on a smaller corpus, reduce `--context-length`. The same checkpoint can serve chat using `AI_PROVIDER=tiny`; for the explicit output path above, also set `ZENITH_TINY_CHECKPOINT` to the absolute path of `artifacts/tiny/model.pt`. Chat needs training text in `System: …`, `User: …`, `Assistant: …` form and a large enough context window. Short training runs will produce poor or meaningless output.

For useful conversation today, use the pretrained open model and fine-tuning workflow above. Training a broadly capable LLM from scratch requires far more data, compute, and evaluation than this small project supplies.

## Deploy

A non-root CPU Docker image, persistent Compose volumes, access-token support, and Hugging Face Docker Space metadata are included. See [deployment instructions](docs/deployment.md).

```bash
# Copy .env.example to .env and set ZENITH_API_TOKEN to a long random token.
# Generate one locally: python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up --build -d
```

Open http://127.0.0.1:7860, expand **Server access**, and enter your token. Docker requires at least 32 characters. Its default network binding is local; use HTTPS and a persistent disk when deploying to a public host.

The installed training/export utilities use the same configured data directory as chat. Default scratch checkpoints and adapters are saved under `ZENITH_HOME/artifacts`; explicit output paths continue to work.

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

Torch-specific checks skip if the optional local dependencies are absent. GitHub Actions runs Python 3.10/3.12 tests on Windows and Linux, plus native installer, cached-model inference, and installed-command checks on both platforms. See [validation notes](docs/validation.md) for checks actually run during development.

This is a single-owner assistant, not a multi-tenant service. The shared access token is not a user-account system. Database files contain conversation text. Model downloads follow the selected Hub revision, use safetensors, and disable remote custom code. Existing starter JSONL files are left untouched; import would need an explicit review because they have no isolated conversation IDs.

## Upstream software

Zenith's code is Apache-2.0, with the original repository license retained. Open weights and dependencies keep their own licenses; weights are downloaded rather than copied into Git. See [upstream references](docs/upstream.md). The original MIT model-card placeholder was replaced with a card appropriate to the default Apache-2.0 Qwen base.
