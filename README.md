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

**A local AI workspace with streamed replies, shorter adaptive reply budgets, a five-component System view, private memories, returning-user greetings, and an owner-controlled security workspace. Browse 1,000 model sources and 200 datasets, collect reviewed examples, and train a measured candidate adapter.** Zenith also includes an original small transformer you can train from random weights.

The original starter ZIP is preserved. Its Python project is now unpacked, extended, and runnable from this repository's root.

**Current release: 0.8.1.** Local-server and Ollama streams now require explicit completion before saving an answer. Bounded HTTP framing handles split Unicode, SSE events, invalid responses, and interrupted connections. File verification, Windows/Linux installers, Docker persistence, and Fast-mode budgets remain supported. See the [changelog](CHANGELOG.md), [provider engineering guide](docs/provider-reliability.md), and [file-integrity guide](docs/integrity.md).

## Upgrade an existing installation

From your existing Zenith folder, stop the running server, then pull and rerun the installer. Your saved profile, accounts, memories, and conversations are retained.

```powershell
# Windows PowerShell
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --mode local
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 --version
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 verify
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 verify --source .
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 serve --warmup
```

```bash
# Linux
git pull --ff-only
bash install.sh --mode local
./run.sh --version
./run.sh verify
./run.sh verify --source .
./run.sh serve --warmup
```

Without Git, download the [complete main source ZIP](https://github.com/jamescartel982-creator/Zenith/archive/refs/heads/main.zip), extract it, and rerun the installer. Preserve any legacy checkout `data/` directory or keep `AGENT_DATA_DIR` pointing to it when changing folders. The source manifest covers all tracked application, installer, test, documentation, catalog, resource, and vendored support files. Separately downloaded model weights, private local settings, chats, and training artifacts are outside that source archive.

## Install locally: Windows or Linux

Python **3.10 or newer** is required; **Python 3.12 is recommended**. Internet is needed for package installation and the first model download. The installer creates a private `.venv`, installs CPU PyTorch when needed, saves user settings, and runs diagnostics. It preserves existing settings and conversations during upgrades.

The current upgrades are merged into `main`. These commands install that version; the source ZIP works without Git.

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
| `--mode ensemble` | Configures Qwen + SmolLM2; Fast uses one routed contributor, Thorough adds review/synthesis | Up to roughly 6–8 GB available RAM and ~1.7 GB weights for the complete team |
| `--mode ollama` | Lightweight Zenith client for an existing Ollama server | Install/start Ollama and pull its configured model separately |
| `--mode localserver` | Lightweight client for a local llama.cpp/vLLM-compatible server | Download a model pack and start a compatible runtime separately |

Append `--download` to a local/ensemble install to cache configured weights during setup. Otherwise, the first message downloads them. Re-running the installer upgrades the application while preserving your profile. Use `--overwrite-config` only when you intend to replace the saved profile; environment variables and a checkout `.env` still take precedence. See [local installation and upgrade instructions](docs/local-installation.md).

### Useful terminal commands

After installation, use the platform wrapper (or the installed `zenith` executable):

```text
zenith chat                    Terminal conversation
zenith serve                   Browser chat on localhost
zenith doctor                  Dependency, storage, and cache checks
zenith verify                  Check installed wheel files against their recorded hashes
zenith verify --source .       Check every inventoried source-release file
zenith models download         Cache configured HF model weights
zenith doctor --inference      Test a real response using cached weights
zenith catalog --validate      Check the 1,000-model / 200-dataset catalog
zenith system                  Inspect the five configured system components
zenith system --metrics        Inspect local server performance as the OS operator
zenith --help                  List all available commands
```

The saved profile and conversations live in `%LOCALAPPDATA%\Zenith` on Windows and `~/.local/share/zenith` on Linux (or `XDG_DATA_HOME/zenith`). `ZENITH_HOME` selects another absolute location. Existing checkout `data/zenith.sqlite3` databases are retained. No paid AI API key is needed; model downloads use open checkpoints. Once cached, `HF_HUB_OFFLINE=1` makes supported HF loads use local files only.

## Your workspace, your memory

In browser chat, select **Sign in / Create account** to keep your conversations and explicitly saved memories together. Zenith greets you with **Welcome back, <name>.** on return. Open **Memory** to save or forget preferences and project context. The refreshed workspace includes the Zenith logo/banner, safe Markdown and code blocks, copy buttons, and recent conversations. No paid AI API key is required. See [account and memory behavior](docs/memory.md), including limits, deletion, and training-context details.

## Three requested Zenith model packs

**Zenith 27B**, **Zenith Vision**, and **Zenith 9B** integrate the three requested N8STORM repositories through complete pinned manifests and a key-free local model-server provider. All **132 upstream files** are inventoried; all **43 non-weight support/source files** are copied under `vendor/model-packs/`. The **89 weight artifacts** remain verified downloads: every variant together is about **685.6 GiB**. The default pack download selects one suitable GGUF rather than every quantization.

```text
zenith packs list
zenith packs files zenith-9b
zenith packs download zenith-9b
```

Use your platform wrapper for these commands, as above. Compatible local runtime setup, full-repository downloads, disk/RAM needs, pinned revisions, and retained attribution are covered in [model pack instructions](docs/model-packs.md). The app uses Zenith display names; loader identifiers and copyright notices are preserved. These large checkpoints have not been benchmarked in Zenith, and the current chat transport is text-only. A different interface and memory do not establish that Zenith outperforms Claude.

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

**Only the configured team runs.** Fast mode, the default, answers with the first successful routed contributor. Thorough mode uses the configured two-model team to share drafts, cross-review, and synthesize a final response. Each answer shows executed stages and any failure/fallback. To customize, copy `config/team.example.json` to an ignored local file and set `ZENITH_TEAM_CONFIG` to that path. Select up to three experts per request from a roster of at most 32, plus an optional reviewer and a synthesizer. The provider cache is bounded; the whole catalog is never loaded into memory.

Datasets are searchable source metadata until imported. Import selected text columns with `python -m scripts.import_dataset`; the local search index can then supply cited excerpts to all models participating in an answer. It does not train weights automatically or download all 200 datasets. See [team and dataset instructions](docs/model-team.md) for exact commands, limits, selection methods, and how to configure larger models.

```bash
python -m scripts.catalog --validate
python -m scripts.catalog --kind model --source huggingface --query Qwen
python -m scripts.catalog --kind dataset --source github
```

## Fast responses, quality checks, and owner controls

Open **System** to inspect Zenith's model, harness, context/memory, infrastructure/data pipeline, and governance/monitoring. Private account metrics show reported tokens and model-generated latency separately from instant built-in checks; the elevated owner can inspect server totals. A bounded GitHub diagnostic workflow checks relevant PRs, `main` updates, and a weekly schedule for regressions.

**Length: Auto** keeps simple fast answers concise with a 96-token maximum, recent context, and shorter instructions. Code/detailed work keeps the full configured budget; **Full** also restores longer history context. The browser can stop generation and continue a capped reply; terminal replies now stream as well. `zenith serve --warmup` moves the first model-load wait to startup. See [the five components, token budgets, monitoring, and limits](docs/system.md).

In a five-question CPU development comparison, prompt tokens fell 41%, reply-text tokens 79%, and median complete replies 47% (13.17 → 6.99 seconds). First-text time did not improve, one request became slower, and factual errors remain. [Raw reports and interpretation](docs/benchmarks/v0.7/) are included; no ChatGPT/Claude speed parity is claimed.

Browser replies stream as they are generated. Choose **Fast** for one routed contributor or **Thorough** for full configured team deliberation. Twelve selectable instruction profiles cover mathematics, science, history, ancient math, programming, investing, day trading, cybersecurity, writing, research, and data analysis. Profiles guide the model; they do not establish expert qualifications. Bounded arithmetic uses an exact calculator. Unavailable live data and some unsupported claims trigger explicit abstention; ordinary model answers remain labeled uncalibrated.

Create your own browser account, then configure its owner role in your server terminal:

```text
zenith admin init --username YOUR_USERNAME
```

Use `./run.sh admin init ...` on Linux or `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 admin init ...` on Windows. A private code is generated **on your machine**, never embedded in Git or sent to the model. Sign in as that account and unlock **Admin workspace**. **Devil mode** enables a short-lived offline workbench: bounded calculator, text hashing, Base64 decoding, pasted-code pattern review, and offline URL inspection. See [owner setup and exact access limits](docs/admin.md).

Signed-in users can request human review of an answer; the owner responds through the local review queue. No outside person is notified automatically.

```text
zenith benchmark --output artifacts/baseline.json
zenith curriculum prepare --balance-topics --output artifacts/curriculum-v1
zenith curriculum audit --output artifacts/curriculum-v1
zenith import-book euclid
zenith campaign --output artifacts/campaign-v1 --max-steps 40
```

Training needs the optional `[train]` dependencies. The campaign freezes grouped training/validation/test partitions, trains a pinned-base adapter, measures held-out loss, compares task slices, and **never activates a candidate automatically**. A manual GitHub Actions training workflow also saves candidate artifacts. The bundled 94-row, ten-topic curriculum is a small original starter set. The Euclid book command adds cited retrieval excerpts, separately from weight training. No collection of every book or every subject has been trained.

See [goals, evaluation, data isolation, calibration, and limitations](docs/quality-and-training.md), the [two-week training roadmap](docs/training-roadmap.md), and [measured development results](docs/validation.md). Faster deterministic paths and earlier streamed text do not establish a faster or more accurate underlying LLM.

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
- `agent/integrity.py`, `release-manifest.json`: installed-file checks and complete source inventory.
- `Dockerfile`, `compose.yaml`: non-root installed runtime and persistent data/profile volumes.

## Documentation

| Guide | Covers |
| --- | --- |
| [Local installation](docs/local-installation.md) | Windows/Linux, saved profiles, upgrades, offline use |
| [System](docs/system.md) | Five components, shorter replies, token reporting, monitoring |
| [Accounts and memory](docs/memory.md) | Private conversations, saved notes, deletion |
| [Owner workspace](docs/admin.md) | Private owner code, expiry/rotation, Devil-mode tools |
| [Model packs](docs/model-packs.md) | All 132 pinned upstream entries, support files, weight downloads |
| [Model team and imports](docs/model-team.md) | Fast/Thorough collaboration, bounded source retrieval |
| [Quality and training](docs/quality-and-training.md) | Versioned data, isolated tests, calibration, human review |
| [Training roadmap](docs/training-roadmap.md) | Bounded experiments and a two-week plan |
| [Deployment](docs/deployment.md) | Docker, persistent storage, hosting, API access |
| [Provider reliability](docs/provider-reliability.md) | Completion checks, bounded HTTP streams, failure recovery |
| [Integrity](docs/integrity.md) | Complete source and installed-package checks |
| [Validation](docs/validation.md) | Actual checks and measured limitations |
| [Changelog](CHANGELOG.md) | Release changes |

## Tests and evidence

```bash
pip install -e ".[test]"
python -m unittest discover -s tests -v
```

Torch-specific checks skip if the optional local dependencies are absent. GitHub Actions runs Python 3.10/3.12 tests on Windows and Linux, plus native installer, cached-model inference, and installed-command checks on both platforms. See [validation notes](docs/validation.md) for checks actually run during development.

Local password accounts isolate browser conversation and memory access; the server operator still controls the database, shared knowledge, configuration, and training tools. The optional shared server access token is an additional gate. See [account limits](docs/memory.md); this is not an audited production multi-tenant service. Database files contain conversation text. Model downloads follow the selected Hub revision, use safetensors, and disable remote custom code. Existing starter JSONL files are left untouched; import would need an explicit review because they have no isolated conversation IDs.

## Upstream software

Zenith's code is Apache-2.0, with the original repository license retained. Open weights and dependencies keep their own licenses; weights are downloaded rather than copied into Git. See [upstream references](docs/upstream.md). The original MIT model-card placeholder was replaced with a card appropriate to the default Apache-2.0 Qwen base.
