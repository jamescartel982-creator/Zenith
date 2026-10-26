# macOS installation

Use Apple Silicon with macOS 14 or newer and **native ARM64 Python 3.12** for
Zenith's existing local Hugging Face model. Keep several GB of free storage and
about 4–6 GB of available RAM. Homebrew users can run:

```bash
brew install python@3.12 git
git clone https://github.com/n8storm/Zenith.git
cd Zenith
bash install.sh --mode local
bash run.sh chat
```

`install.sh` prefers Python 3.12, honors an explicit `ZENITH_PYTHON`, and creates
`.venv`. No system package changes, administrator password or API key are needed
by Zenith's installer. Homebrew installation itself is separate.

To open the browser interface, use `bash start.sh`, or double-click **Install
Zenith.command** for first setup and **Start Zenith.command** later. If macOS
requires approval for a downloaded file, inspect the source and use Finder's
Open action or the terminal command; do not disable system security globally.
Keep the terminal running during the session. Terminal chat remains available.

## Platform boundary

Current supported PyTorch wheels on PyPI are macOS 14+ ARM64. The Linux/Windows
CPU package index does not supply the native Mac wheel. The installer uses PyPI
on Mac and keeps the same secure dependency floor; it never installs an obsolete
Intel build or changes the model silently. Running Intel Python under Rosetta on
Apple Silicon also fails this native runtime check: install native ARM64 Python.

Intel or older Macs may install Zenith's core app using an **explicitly chosen**
external provider:

```bash
bash install.sh --mode localserver
```

On Intel, the security dependencies currently build from source when a compatible
wheel is unavailable. Install Apple's command-line tools (if absent) and the
build prerequisites first; this does not change Zenith's model or dependency
security floors:

```bash
xcode-select --install
brew install rust openssl@3 pkg-config libffi
bash install.sh --mode localserver
```

Wait for the Xcode installer to finish before running the following commands.
If the tools are already installed, skip `xcode-select --install`. Building
cryptography can take several minutes. These are separate host prerequisites;
Zenith does not install them globally on your behalf. See the
[official cryptography macOS build requirements](https://cryptography.io/en/latest/installation/#building-cryptography-on-macos).

Configure and run a compatible inference backend separately. This is not a claim
that the preserved Hugging Face model runs natively on Intel. Existing profiles
are preserved; the effective saved backend determines required dependencies.

Device selection remains CUDA → available MPS → CPU. `--runtime cpu` chooses
wheel distribution; set `ZENITH_DEVICE=cpu` to force inference onto CPU. Apple
Silicon CI uses CPU for reproducibility. Physical Metal/MPS acceleration and
Finder GUI behavior require a physical Mac and are not established by hosted CI.

## Verification, updates and rollback

The `macOS installation` workflow exercises native installation, the original
checkpoint, isolated adapter activation/rollback and app/security regressions on
Apple Silicon; Intel exercises the core app and explicit external backend only.
Consult its actual run results before treating a platform as verified.

Use `git pull --ff-only` and rerun `bash install.sh --mode local` on supported
native Macs. The installer preserves existing profile, accounts, conversations,
model weights, tokenizer and selected adapters. For a code rollback, check out
the previous release commit and reinstall that version in a separate environment;
retain the profile and deployment receipts. Do not overwrite original checkpoints.
