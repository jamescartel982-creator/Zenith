---
title: Zenith
emoji: ⚡
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
license: apache-2.0
---

![Zenith — white pixel typography and a geometric emblem on black.](assets/zenith-banner.png)

# Zenith

A local AI workspace for conversations, coding, research, and reviewed learning. Zenith brings open model runtimes, private memory, streamed responses, and evaluation tools into a single application for Windows and Linux.

**Release 0.11.1** · [Changelog](CHANGELOG.md) · [Installation](docs/local-installation.md) · [Model discovery](docs/model-discovery.md) · [Validation](docs/validation.md)

## Install

Install [Python 3.12](https://www.python.org/downloads/) first. On Windows, enable **Add Python to PATH**. Initial setup needs internet access and enough space for Python packages and the local model. The small default model typically needs about 4–6 GB of available RAM.

### Windows: download, extract, double-click

1. [Download Zenith](https://github.com/jamescartel982-creator/Zenith/archive/refs/heads/main.zip) and **extract the ZIP**.
2. Open the extracted Zenith folder and double-click **Install Zenith.cmd**.
3. Wait for setup and the model download. Zenith opens in your browser when ready.

Next time, double-click **Start Zenith.cmd**. Keep its terminal window open while using Zenith; press **Ctrl+C** to stop. No Git, manual environment activation, or permanent PowerShell policy change is needed. Keep the extracted files together.

If you already cloned the repository, run `& ".\Install Zenith.cmd"` in PowerShell from the Zenith folder, or double-click it in File Explorer.

### Linux: install and open

Extract the [source ZIP](https://github.com/jamescartel982-creator/Zenith/archive/refs/heads/main.zip), open a terminal in the extracted folder, and run:

```bash
bash install.sh --launch
```

Next time:

```bash
bash start.sh
```

On Debian/Ubuntu, install `python3-venv` if it is missing. If a browser cannot open automatically, visit **http://127.0.0.1:7860**. Keep the terminal open and use **Ctrl+C** to stop Zenith. You can also clone with Git instead of downloading the ZIP.

The installer creates and verifies an isolated `.venv`, preserves existing settings, downloads the configured Hugging Face model before launching, and selects the environment automatically. The first setup may take several minutes depending on your connection. No paid AI API key is required. Existing Ollama or local-server configurations are preserved and require their separate runtime to be running.

For terminal chat, use `./run.sh chat` on Linux or `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 chat` on Windows. Manual activation is available for advanced `zenith`, `python`, and `pip` commands; see [installation details](docs/local-installation.md).

### Runtime choices

| Installer mode | Runtime | Intended use |
| --- | --- | --- |
| `--mode local` | A small, pinned Hugging Face instruction checkpoint | First installation and CPU use |
| `--mode ensemble` | A configured model team with routing, review, and synthesis | Comparing collaborative response strategies |
| `--mode ollama` | An existing local Ollama server | Models managed by Ollama |
| `--mode localserver` | A compatible local llama.cpp or vLLM server | Separately downloaded model packs |

Local mode typically needs about 4–6 GB of available RAM and roughly 1 GB for weights. Append `--download` to cache the configured Hugging Face weights during installation; otherwise they download when first used. External runtimes must be installed and started separately. See [runtime setup](docs/local-installation.md) and [model packs](docs/model-packs.md).

## Workspace

- **Conversation:** streamed replies, code formatting, response budgets, and Fast or Thorough processing modes.
- **Memory:** local accounts, welcome-back greetings, private conversation history, and notes you explicitly choose to save or forget.
- **Model discovery:** search Hugging Face and GitHub on demand, including fine-tuned model repositories, and save selected source references locally.
- **Skills:** conversation profiles activated with `/skill list`, `/skill mathematics`, `/skill status`, or `/skill off`.
- **Owner controls:** defensive security profiles require the configured owner account and a current private admin-code unlock.
- **Learning and evaluation:** reviewed examples, versioned data splits, candidate training, regression checks, and recorded performance.

The System view shows the model, interface, context and memory, infrastructure and data pipeline, and governance and monitoring components. Engineering standards are implemented in the application and documented in [engineering](docs/engineering.md).

## Discover and configure models

Choose **Browse catalog → Search online**, then select Hugging Face or GitHub. Public model search includes base checkpoints, fine-tunes, adapters, merges, and quantized repositories. Source metadata and lineage appear when published by the author. The bundled catalog remains available offline.

```bash
zenith discover search --source huggingface --query Qwen
zenith discover search --source github --query "topic:llm"
zenith discover add --source huggingface --id OWNER/MODEL
zenith discover list
```

Replace `OWNER/MODEL` with the actual source identifier. Saving imports metadata into your local catalog; configure a compatible provider explicitly to run the selected model. Keep its original identifier and pinned revision. Model packs provide file manifests and optional verified downloads for compatible local servers.

Source APIs have access, pagination, and rate limits. A repository may require different hardware, an unsupported architecture, or additional licensing permissions. Discovery does not bundle every public model, execute repository code, merge weights, or train Zenith on source content. See [discovery and compatibility](docs/model-discovery.md).

## Verify and update

After activation:

```bash
zenith --version
zenith doctor
zenith verify
zenith verify --source .
zenith doctor --inference
```

`doctor --inference` tests a real response and may download the configured checkpoint. `verify` checks the installed wheel; `verify --source .` checks the source release inventory. Pip’s **“No broken requirements found” means its dependency check passed**. The installer presents that result as **“Dependencies verified. No package conflicts detected.”**

To upgrade, stop Zenith, run `git pull --ff-only` if you use Git, then rerun **Install Zenith.cmd** on Windows or `bash install.sh --launch` on Linux. Existing configuration and conversations are preserved. Without Git, use the [source ZIP](https://github.com/jamescartel982-creator/Zenith/archive/refs/heads/main.zip) and preserve any legacy checkout `data/` directory. See [upgrade instructions](docs/local-installation.md).

## Privacy and administration

Profiles and application data live under `%LOCALAPPDATA%\Zenith` on Windows or `~/.local/share/zenith` on Linux. `ZENITH_HOME` selects another location. Cached Hugging Face models support `HF_HUB_OFFLINE=1`; `ZENITH_DISCOVERY_OFFLINE=1` disables online discovery. Online search sends the query to the selected source; external model servers receive the context supplied to them.

Create a browser account, then configure the owner from your activated terminal:

```text
zenith admin init --username YOUR_USERNAME
```

The unique code is created locally and kept out of model prompts and Git. Sign in as the owner and unlock Admin before explicitly activating a protected security profile. Logout, locking, code rotation, and expiry revoke that access. See [administration](docs/admin.md), [skills](docs/skills.md), and [memory](docs/memory.md). Shared deployments require the authentication and network controls in [deployment](docs/deployment.md).

## Development and limitations

Zenith supports reviewed LoRA candidates and an experimental transformer trained from random weights. Training is explicit; ordinary chat does not update model weights. Evaluation and review determine whether a candidate should replace a baseline. The project does not claim comprehensive knowledge, professional certification, or performance parity with proprietary assistants. Response speed and quality depend on the configured model, hardware, context, and processing mode.

```bash
python -m pip install -e ".[test]"
python -m unittest discover -s tests -v
zenith catalog --validate
zenith skills validate
```

See [training](docs/quality-and-training.md), [training roadmap](docs/training-roadmap.md), [benchmarks](docs/benchmarks/v0.7/), and [validation evidence](docs/validation.md). Zenith’s code is licensed under [Apache-2.0](LICENSE); third-party model, dataset, and vendored-file terms remain applicable. The original starter archive is preserved in the repository.
