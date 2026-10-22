# Install, run, and upgrade Zenith locally

The Windows and Linux installers share `install.py`, a standard-library bootstrap. Thin shell wrappers choose Python and forward your arguments. They install Zenith as a normal wheel into `.venv`; runtime commands can then work outside the checkout. No virtual-environment activation is required when using `run.ps1`, `run.sh`, or the absolute installed executable path.

## Requirements

- Python 3.10+; Python 3.12 is recommended. Python 3.10 and 3.12 are covered by platform CI.
- Python venv support. Debian/Ubuntu may require `python3-venv`; the python.org Windows installer includes it.
- Internet for Python dependencies and initial model weights; several GB of disk space.
- The small single model needs roughly 4–6 GB available RAM. The two-model team needs roughly 6–8 GB. CPU inference is supported; a GPU is optional.
- Git to clone the current branch, or download/extract the branch ZIP instead.

The complete project is merged into `main`. Clone `https://github.com/jamescartel982-creator/Zenith.git` using the commands in the README. If you already have the preview branch checked out, run `git fetch origin`, `git switch main`, and `git pull --ff-only`, then re-run your platform's installer.

## Windows PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --mode local
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 chat
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 serve
```

The last command starts http://127.0.0.1:7860. Use Ctrl+C to stop the server. Windows Terminal/PowerShell 7 is convenient, and Windows PowerShell 5.1 is supported by the wrappers. The temporary execution-policy argument changes only that launched process.

You can also call the installed executable directly:

```powershell
& ".\.venv\Scripts\zenith.exe" --help
& ".\.venv\Scripts\zenith.exe" models download
& ".\.venv\Scripts\zenith.exe" doctor --inference
```

If Python is missing, install it from python.org or `winget install -e --id Python.Python.3.12`, then reopen the terminal. If several Python versions are installed, set `$env:ZENITH_PYTHON` to the intended interpreter's absolute path before invoking `install.ps1`.

## Linux

```bash
bash install.sh --mode local
./run.sh chat
./run.sh serve
```

On Debian/Ubuntu, install prerequisites if needed:

```bash
sudo apt update
sudo apt install python3 python3-venv git
```

Direct executable use:

```bash
.venv/bin/zenith --help
.venv/bin/zenith models download
.venv/bin/zenith doctor --inference
```

For a specific interpreter: `ZENITH_PYTHON=/path/to/python3.12 bash install.sh --mode local`.

## Mode and runtime choices

The default installer mode is `local`: a single small instruction model with CPU PyTorch. `--mode ensemble` enables the two-model draft/review/synthesis pipeline. `--mode ollama` installs the lightweight client without Torch/Transformers when that is the effective configured provider. Install/start Ollama separately and run `ollama pull qwen2.5-coder:7b` before chatting.

`--runtime cpu` is the default and uses PyTorch's official CPU wheel index. For an accelerator build, use `--runtime auto` and follow PyTorch's current instructions for your hardware/driver; the ordinary distribution is not a guarantee that every GPU is supported. `ZENITH_DEVICE=auto` selects supported CUDA/MPS/CPU at runtime. `ZENITH_CPU_THREADS` bounds CPU inference threads (default at most four).

The bootstrap first reads the effective configuration after preserving or writing your profile, then installs dependencies for that provider. Existing Ollama users therefore avoid an accidental Torch download when re-running the default installer. `--download` proactively caches HF weights; otherwise the first chat performs the initial download. Model files are never bundled into Git.

`--venv /absolute/path` selects another virtual environment. The checkout wrappers always target the checkout's `.venv`; for a custom environment, use the executable path printed by the installer.

## Saved settings and data

Defaults:

| OS | User directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\Zenith` |
| Linux | `~/.local/share/zenith`, or `$XDG_DATA_HOME/zenith` |

The directory contains `config.env`, `data/` with conversations/imported knowledge/exports, and default `artifacts/` output from training. Set `ZENITH_HOME` to an **absolute path** for another location. `ZENITH_CONFIG_FILE` can select a separate config file. Downloads follow the normal Hugging Face cache location; `HF_HOME` can move that cache.

Configuration precedence is explicit environment variables, then `.env` in the current working directory, then the saved user profile. Relative paths in an explicit `.env` or environment variable are relative to that working directory. Fresh user defaults are stable when you launch from different directories. An existing checkout `data/zenith.sqlite3` is retained so upgrades do not silently switch away from old conversations; set `AGENT_DATA_DIR` to its absolute path when resuming it from elsewhere.

Change the saved mode explicitly:

```text
zenith configure --mode ensemble --overwrite
```

Use your platform wrapper or installed executable for that command. `--overwrite` replaces the saved profile, so retain any custom values you need first. Project `.env` and external environment overrides remain in control.

Training export, evaluation, and default dataset inputs use the same configured data directory. Explicit `--train-data`, `--eval-data`, `--output-dir`, and adapter paths still work. Run `zenith <command> --help` for the relevant utility.

## Diagnostics and offline use

`zenith doctor` checks dependency presence, writable SQLite/FTS storage, disk/RAM, configuration, and cached files. It does not download or execute a model. Missing cached weights produce a warning; the installer can still finish so you can download them later.

`zenith models download` caches configured HF weights. `zenith models check` checks existing files without a network request. `zenith doctor --inference` then runs a short real response; it requires cached HF files. A successful diagnostic is a readiness check, not a broad quality benchmark. In ensemble mode, the report also warns if some stages degrade.

Use `HF_HUB_OFFLINE=1` after caching to force supported HF model loads to local files. Adapters need their own cached/local files as well. Catalog search and local dataset retrieval remain available offline; refreshing source metadata and importing remote datasets need network access.

## Upgrade

From the checkout, pull your branch and re-run the installer you used:

```bash
git pull --ff-only
bash install.sh
```

On Windows, use `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1` after `git pull --ff-only`. Existing profiles, datasets, checkpoints, and conversations are preserved. Package versions are resolved within the project's compatible dependency families. The installer does not delete/recreate an existing environment or force a global Python upgrade.

If you intentionally want a fresh profile, use `--overwrite-config`. To experiment with another Python version, choose a new `--venv` path rather than overwriting an unrelated environment.

## Common problems

- **`python` / `py` missing:** install Python 3.12, reopen the terminal, or set `ZENITH_PYTHON` explicitly.
- **`ensurepip` / venv unavailable:** install the platform's Python venv component, then re-run the installer.
- **An old venv uses the wrong Python:** use a new `--venv` directory with the supported interpreter.
- **Missing dependencies after selecting another mode:** rerun the installer; it reads the effective profile/environment and installs for that provider.
- **Install failed:** the bootstrap stops with a nonzero exit code; inspect the preceding pip/config error and retry. It preserves the environment and saved data.
- **`zenith` not found by the shell:** use `run.ps1`/`run.sh` or the installed executable path. An optional venv activation makes the short name available in that terminal session.
- **Model unavailable:** run `doctor`, `models download`, then `doctor --inference`. Check RAM/disk and model access. Ollama needs its running server and pulled model.
- **Slow answers:** select `--mode local`, reduce `MAX_NEW_TOKENS`, or configure suitable hardware. The model-team mode deliberately makes several calls.
- **Port 7860 occupied:** use `zenith serve --port 7861` through your wrapper/executable.
