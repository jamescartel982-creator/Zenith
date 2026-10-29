---
title: Zenith
license: apache-2.0
---

![Zenith — your local AI workspace.](assets/zenith-social-preview.png)

# Zenith

Zenith lets you run AI models on your own computer for chat, coding, and research. It keeps conversation history and saved notes locally, and includes tools for trying different models, training candidates, and checking how they perform.

It runs on Windows, Linux, and supported Macs. You can start with the included local setup or connect a runtime you already use, such as Ollama.

**Release 0.17.4** · [Changelog](CHANGELOG.md) · [Installation](docs/local-installation.md) · [Model discovery](docs/model-discovery.md) · [Validation](docs/validation.md) · [Security](SECURITY.md)

## Install

Python 3.12 is recommended. The local setup doesn't need a paid API key.

### Windows

Install Python from PowerShell:

```powershell
winget install -e --id Python.Python.3.12
```

Reopen PowerShell, then run:

```powershell
git clone https://github.com/n8storm/Zenith.git
cd Zenith
py -3.12 install.py --mode local
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 chat
```

If PowerShell doesn't recognize `git`, install it with the command below, reopen PowerShell, and try cloning again:

```powershell
winget install -e --id Git.Git
```

### Linux

```bash
git clone https://github.com/n8storm/Zenith.git
cd Zenith
python3 install.py --mode local
bash run.sh chat
```

On Debian or Ubuntu, you may need to install `python3-venv` and Git first.

### macOS

For Apple Silicon Macs running macOS 14 or later, use native ARM64 Python 3.12. With Homebrew already installed:

```bash
brew install python@3.12 git
git clone https://github.com/n8storm/Zenith.git
cd Zenith
bash install.sh --mode local
bash run.sh chat
```

The launcher selects Python 3.12 automatically. If you prefer a browser window, double-click **Install Zenith.command** for setup, then **Start Zenith.command** on later visits.

On an Intel Mac, use `bash install.sh --mode localserver` and configure a compatible backend running separately. Current secure native PyTorch wheels are ARM64-only. See [Mac support and limitations](docs/macos.md).

### After installation

The installer creates and uses `.venv` for you. The small local model needs about 4–6 GB of available RAM, roughly 1 GB for weights, and several GB of disk space overall. It downloads on first use; add `--download` to the install command if you'd rather download it during setup.

Next time, open the Zenith folder and run the same `run.ps1 chat` or `bash run.sh chat` command. Type `/quit` to leave terminal chat.

You can also add `--activate-candidate` to the install command to try the combined experimental model. It has known quality regressions. Activation records your acceptance of those regressions, verifies and caches the weights, and saves a rollback receipt. Your settings and conversations are kept. See [installation details](docs/local-installation.md).

### Choose a runtime

| Installer mode | What it uses | When to choose it |
| --- | --- | --- |
| `--mode local` | A small Hugging Face instruction model pinned to a specific revision | Start here, including on CPU |
| `--mode ensemble` | Several configured models that draft, review, and combine replies | Try different ways of working with multiple models |
| `--mode ollama` | A local Ollama server | You already manage models with Ollama |
| `--mode localserver` | A compatible llama.cpp or vLLM server | You have a separate server or downloaded model pack |

Install and start external runtimes separately. See [runtime setup](docs/local-installation.md) and [model packs](docs/model-packs.md).

If you're working on the Hermes/OpenClaw integrations, use their separate [pinned runtime setup](integrations/runtime_setup/README.md) for Node, Python, and protocol test SDKs.

## What you can do

- **Chat:** get streamed replies with code formatting, set response budgets, and choose Fast or Thorough processing.
- **Keep useful context:** use local accounts and private conversation history, with notes you choose to save or forget.
- **Find models:** search Hugging Face and GitHub, including fine-tunes, and save references to your local catalog.
- **Switch conversation profiles:** try `/skill list`, `/skill mathematics`, `/skill status`, or `/skill off`.
- **Manage protected profiles:** defensive security profiles require the owner account and a current private admin-code unlock.
- **Test and train:** review examples, keep versioned data splits, train candidates, and check for regressions.

The System view shows how the model, interface, memory, infrastructure, data pipeline, and monitoring fit together. See [engineering](docs/engineering.md) for the implementation standards.

## Find and configure models

Open **Browse catalog → Search online** and choose Hugging Face or GitHub. Search covers base models, fine-tunes, adapters, merges, and quantized repositories. You'll see source metadata and model lineage where the author provides them. The bundled catalog also works offline.

From the terminal:

```bash
zenith discover search --source huggingface --query Qwen
zenith discover search --source github --query "topic:llm"
zenith discover add --source huggingface --id OWNER/MODEL
zenith discover list
```

Replace `OWNER/MODEL` with the model's source identifier. Adding a model saves its metadata; you'll still need to configure a compatible provider to run it. Keep the original identifier and pinned revision. Model packs include file manifests and optional verified downloads for compatible local servers.

Check a model's hardware needs, architecture, and license before using it. Source APIs also have access, pagination, and rate limits. Finding a repository doesn't run its code, merge its weights, or use its content to train Zenith. See [discovery and compatibility](docs/model-discovery.md).

## Optional features

### Work with multiple models

The [model registry and orchestrator](docs/platform-models.md) let you keep discovery scoped to an account, route requests between providers, and have models draft and review replies together. External providers need their own credentials and must be enabled explicitly. Your normal chat configuration, model weights, and tokenizer stay the same.

See the [repository audit](docs/platform-audit/README.md) and [measured results](docs/platform-audit/results.md).

Authenticated Hugging Face Qwen2 conversations can reuse private attention state between requests. Tests found roughly 9–14× faster follow-ups on repeated long-context arithmetic, with unchanged weights and exact paired answers. That result is specific to those tests; fresh requests and other providers have different limits. See [latency results and configuration](docs/benchmarks/scoped-kv/README.md).

### Give a problem more than one pass

```bash
zenith reason "Explain this problem." --effort standard
```

You can also choose Fast, Deep, or Research effort. The [reasoning guide](docs/reasoning/README.md) explains how Zenith generates candidates, reviews them separately, checks exact arithmetic, and runs restricted numeric code tests with owner authorization. All passes share a fixed budget and leave weights and installation settings unchanged.

The small native model still struggles to produce structured reviews. The [diagnostic results](docs/reasoning/native-diagnostics.json) don't establish a general improvement in quality or speed.

### Queue supervised tasks

The [supervised task pilot](docs/platform/operations.md) supports authenticated local chat queues, fixed diagnostic plans, approval for specific network actions, and saved task events with audit checks. It's disabled by default and keeps your current installation, provider, weights, tokenizer, and data.

This stage doesn't include autonomous tools, plugins, or browser/channel automation. See [implementation boundaries](docs/platform/architecture.md) and [measured results](docs/platform/benchmark-results.md).

### Run isolated Python

The [isolated Python tool](docs/unified-platform/sandbox.md) runs approved programs in temporary offline Linux containers. To use it, you need owner MFA, a scoped grant, a reviewed image pinned to a specific version, and explicit opt-in. Queued runs also need approval for the exact action. If isolation isn't available, the program won't run on the host instead.

The [OpenClaw/Hermes audit](docs/unified-audit/README.md) tracks the remaining work. This feature keeps the existing Zenith model and normal installation; it doesn't yet match all reference features.

## Integration work in progress

Zenith remains the primary model. Hermes, OpenClaw, and TradingAgents have been audited against specific source commits, with their code, licenses, state, and dependencies kept separate.

The bridge between the four runtimes and the compatible inference sidecar are **planned, not operational**. Live trading is disabled.

[Audit](docs/four-system/AUDIT.md) · [Implementation plan](docs/four-system/FILE_BY_FILE_PLAN.md) · [Acceptance gates](docs/four-system/ACCEPTANCE.md)

![Planned four-system architecture; dashed connections are not implemented.](assets/four-system-architecture.svg)

<details>
<summary>TradingAgents architecture and source map</summary>

The diagram maps each component in the reference to its pinned source. The native backtester scores historical decisions; it doesn't simulate a portfolio of filled orders. Historical data checks also can't remove future knowledge already in a model's weights.

![Source-verified TradingAgents architecture.](assets/tradingagents-architecture.svg)

[Component source map](docs/four-system/DIAGRAM_SOURCE_MAP.md) · [Native baseline](docs/four-system/BASELINE.md)

</details>

## Check your installation and update

With your environment activated, run:

```bash
zenith --version
zenith doctor
zenith verify
zenith verify --source .
zenith doctor --inference
```

`doctor --inference` tries a real response and may download the configured model. `verify` checks the installed wheel; `verify --source .` checks the source release inventory.

If pip says “No broken requirements found,” the dependency check passed. The installer displays this as “Dependencies verified. No package conflicts detected.”

To update:

1. Stop Zenith and activate `.venv`.
2. Run `git pull --ff-only`.
3. Run `python -m pip install --upgrade ".[local]"`.

Your configuration and conversations are kept. To try the bundled experimental model, run `zenith setup --activate-candidate`; see the quality caveats below first.

If you don't use Git, download the [source ZIP](https://github.com/n8storm/Zenith/archive/refs/heads/main.zip) and keep any `data/` directory from an older checkout. See [upgrade instructions](docs/local-installation.md).

## Privacy and owner access

Profiles and app data are stored in:

- Windows: `%LOCALAPPDATA%\Zenith`
- Linux: `~/.local/share/zenith`

Set `ZENITH_HOME` to use another location. For cached Hugging Face models, `HF_HUB_OFFLINE=1` enables offline use. Set `ZENITH_DISCOVERY_OFFLINE=1` to turn off online discovery.

Online searches send your query to the source you choose. External model servers receive the context you send them.

To set up owner access, create a browser account, then run this in your activated terminal:

```text
zenith admin init --username YOUR_USERNAME
```

The admin code is generated locally and kept out of model prompts and Git. Sign in as the owner and unlock Admin to activate a protected security profile. Logging out, locking, rotating the code, or letting it expire revokes access.

See [administration](docs/admin.md), [skills](docs/skills.md), and [memory](docs/memory.md). For a shared deployment, follow the authentication and network setup in [deployment](docs/deployment.md).

## Training and experimental models

Ordinary chat doesn't update model weights. Training is a separate step, and candidates need evaluation and review before replacing a baseline.

You can continue training the existing Zenith adapter into a separate candidate while preserving its architecture, tokenizer, and parent file hashes. The pipeline supports instruction tuning, continued training on domain text, reviewed preference pairs, historical replay, raw-model diagnostics, and local merge/export checks. It doesn't promote or publish candidates automatically.

In the recovery study, one candidate scored 24/24 on the public diagnostics but still showed problems in manual review and independent tests. It failed quality review, and that result remains recorded. Promotion checks now look at individual cases as well as scores for groups of cases.

The [experimental research snapshot](research_checkpoints/recovery-v1/) contains the continued adapter weights, original tokenizer, pinned base identity, and training history. You can inspect it, use it for further experiments, or activate it with `zenith setup --activate-candidate`. Activation records an exception for its known regressions; it doesn't mark the candidate as having passed review. Installing the package alone keeps your selected model.

See [recovery results](docs/model-recovery.md), [activation and rollback](docs/model-promotion.md), the [original pilot](docs/continued-training.md), and the [model card](docs/MODEL_CARD.md).

Owner controls include Argon2id password migration, authenticator MFA, explicit capability grants, limited target scopes, activity records, fixed-budget diagnostic plans, and emergency shutdown. Restricted execution starts disabled, even for the owner. Conversation summaries belong to the account and add context without changing model weights. See [execution and memory controls](docs/execution-controls.md).

## Development

Zenith supports reviewed LoRA candidates and an experimental transformer trained from random weights. Speed and response quality depend on the model, hardware, context, and processing mode. The project doesn't claim comprehensive knowledge, professional certification, or parity with proprietary assistants.

```bash
python -m pip install -e ".[test]"
python -m unittest discover -s tests -v
zenith catalog --validate
zenith skills validate
```

See [training](docs/quality-and-training.md), the [training roadmap](docs/training-roadmap.md), [benchmarks](docs/benchmarks/v0.7/), and [validation evidence](docs/validation.md).

Zenith's code is licensed under [Apache-2.0](LICENSE). Third-party models, datasets, and vendored files have their own terms. The original starter archive is also kept in the repository.
