# Install, run, and upgrade Zenith locally

The primary installation flow is Git clone, `install.py --mode local`, and
terminal chat through the platform launcher. The installer creates and selects
its private `.venv` automatically.

Windows PowerShell:

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

If Git is missing, run `winget install -e --id Git.Git`, reopen PowerShell,
and retry. Linux uses `python3 install.py --mode local` and `bash run.sh chat`
after cloning and entering the repository.

Add `--activate-candidate` to the installer to explicitly select the experimental
checkpoint and accept its recorded regressions. Its receipt preserves the failed
quality decision and rollback information. Without that option, existing model
selection is preserved. Bare `zenith` commands require environment activation;
the platform launchers select the environment directly.

The standalone `quickstart.py` remains an optional download helper. It verifies
source checksums and reuses a verified existing directory without replacing local
edits. Its default location is `~/Zenith`; `--directory PATH` selects another
folder, and `--no-launch` installs without starting the app. It does not refresh
an existing checkout from a different revision. Use `git pull --ff-only` to update
a clone. Checksums establish byte consistency; the official HTTPS repository is
the download trust source.

For CPU-only PyTorch, install it before the local extra:

```bash
python -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
python -m pip install ".[local]"
```


The Windows and Linux installers share `install.py`, a standard-library bootstrap. Thin shell wrappers choose Python and forward your arguments. They install Zenith as a normal wheel into `.venv`; runtime commands can then work outside the checkout. No virtual-environment activation is required when using `run.ps1`, `run.sh`, or the absolute installed executable path.

## Quick setup

Windows users can download/extract the [source ZIP](https://github.com/n8storm/Zenith/archive/refs/heads/main.zip), then double-click **Install Zenith.cmd**. Python 3.12 should already be installed with **Add Python to PATH** enabled. Setup installs the configured runtime, verifies dependencies and package files, downloads configured Hugging Face weights, and opens the local browser workspace. Run **Start Zenith.cmd** on later visits. Git and environment activation are optional for this flow; ZIP contents must be extracted and kept together.

Linux users run `bash install.sh --launch` from the extracted or cloned folder. Run `bash start.sh` on later visits. Both launchers select the private virtual environment automatically. Keep the terminal open while using Zenith; Ctrl+C stops the server. Headless systems can open the printed localhost URL manually or forward the port as appropriate for their environment.

The terminal equivalent on Windows is `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --launch`. The policy argument applies only to that process. `--launch` can be combined with normal installer mode/runtime options; a custom `--venv` is used for immediate launch, while the checkout start scripts always use `.venv`. On a custom environment, use the absolute browser command printed by setup on later visits.

`zenith serve --open-browser` opens the browser only after its own server starts. A failed startup does not open an unrelated service already occupying the port. If no browser is available, the URL remains in the terminal. CLI scripts and CI can set `ZENITH_NO_PAUSE=1` to prevent Windows launchers from pausing on errors. There is no automatic login, password generation, or external AI API-key setup.

## Requirements

- Python 3.10+; Python 3.12 is recommended. Python 3.10 and 3.12 are covered by platform CI.
- Python venv support. Debian/Ubuntu may require `python3-venv`; the python.org Windows installer includes it.
- Internet for Python dependencies and initial model weights; several GB of disk space.
- The small single model needs roughly 4–6 GB available RAM. The two-model team needs roughly 6–8 GB. CPU inference is supported; a GPU is optional.
- Git to clone the current branch, or download/extract the branch ZIP instead.

The complete project is merged into `main`. Clone `https://github.com/n8storm/Zenith.git` using the commands in the README. If you already have the preview branch checked out, run `git fetch origin`, `git switch main`, and `git pull --ff-only`, then re-run your platform's installer.

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

## Activate the environment

The isolated environment is required for installation. Activate it in each terminal before using bare `zenith`, `python`, or `pip` commands:

```powershell
# Windows PowerShell; execution policy changes only for this process.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\activate.ps1
zenith doctor
```

```bash
# Linux Bash
source ./activate.sh
zenith doctor
```

Run `deactivate` to leave. Source the helper in the current shell; executing it as a child process cannot activate the parent terminal. With a custom `--venv` path, use the exact activation path printed by the installer instead. Checkout run scripts and absolute installed executable paths select the correct environment directly.

The installer checks that its selected Python belongs to a virtual environment before running pip. The message **Dependencies verified. No package conflicts detected.** means `pip check` succeeded; pip's original **No broken requirements found** is also a success result. Actual package conflicts retain their error output and stop installation. A successful dependency check does not prove that an external runtime is running or that model weights are compatible; use `doctor --inference` for a real response check.

## Mode and runtime choices

The default installer mode is `local`: a single small instruction model with CPU PyTorch. `--mode ensemble` configures the small team: Fast uses one routed contributor; Thorough performs draft/review/synthesis. `--mode localserver` installs the key-free local llama.cpp/vLLM client; see [model packs](model-packs.md). `--mode ollama` installs the lightweight client without Torch/Transformers when that is the effective configured provider. Install/start Ollama separately and run `ollama pull qwen2.5-coder:7b` before chatting.

`--runtime cpu` is the default and uses PyTorch's official CPU wheel index. For an accelerator build, use `--runtime auto` and follow PyTorch's current instructions for your hardware/driver; the ordinary distribution is not a guarantee that every GPU is supported. `ZENITH_DEVICE=auto` selects supported CUDA/MPS/CPU at runtime. `ZENITH_CPU_THREADS` bounds CPU inference threads (default at most four).

The bootstrap first reads the effective configuration after preserving or writing your profile, then installs dependencies for that provider. Existing Ollama users therefore avoid an accidental Torch download when re-running the default installer. `--download` proactively caches HF weights; otherwise the first chat performs the initial download. The pinned base is downloaded separately. The experimental adapter is bundled as verified research weight parts.

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

`zenith models download` caches configured HF weights. `zenith models check` checks existing files without a network request. `zenith doctor --inference` then runs a short real response; it requires cached HF files. A successful diagnostic is a readiness check, not a broad quality benchmark. In ensemble Fast mode, the inference probe runs one actual routed model and does not require the unused reviewer cache. Thorough checks the complete team and warns about degraded stages.

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
- **Slow answers:** choose Fast + Auto/Brief, use `serve --warmup`, or configure suitable hardware. Thorough deliberately makes several model calls; Full raises context/output use.
- **Port 7860 occupied:** use `zenith serve --port 7861` through your wrapper/executable.

## Release file checks

After upgrading, run `zenith --version`, `zenith verify`, and `zenith verify --source PATH_TO_CHECKOUT` through your wrapper. Installed verification checks the wheel; source verification checks the complete tracked manifest and works with ZIP extraction. Editable development installs must use source verification. See [integrity checks](integrity.md) and the [changelog](../CHANGELOG.md). Existing optional calibration artifacts must match the new release configuration before use.

### Repository owner update

The canonical repository is now `https://github.com/n8storm/Zenith`. Existing Git
checkouts can update their remote without recloning or changing local data:

```bash
git remote set-url origin https://github.com/n8storm/Zenith.git
git pull --ff-only
```

Then activate the existing environment and reinstall using the upgrade steps
above. Historical pinned audit evidence retains the recorded owner name and
checksums; the repository identity and trained model are unchanged.
