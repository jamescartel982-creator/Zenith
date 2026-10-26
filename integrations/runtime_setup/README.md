# Isolated integration prerequisites

This optional setup installs runtimes and bridge test SDKs outside Zenith and
the audited Hermes/OpenClaw source trees. It does not start an agent, change a
model, install the native projects' complete dependency sets, or complete the
runtime bridge. Zenith's normal installation commands remain unchanged.

## Pins and compatibility

| Component | Selected pin | Source requirement |
| --- | --- | --- |
| Zenith | Existing Python 3.12 environment | `pyproject.toml`: Python >=3.10 |
| Hermes managed Python and bridge SDK Python | CPython 3.14.8 | Hermes `.python-version`: 3.14; `pm/pyproject.toml`: >=3.14,<3.15 |
| Node | 26.12.1 | OpenClaw: >=24.22.1 <25 or >=26.12.1; Hermes: >=26 |
| npm | 11.17.0 | Hermes: <11.10.0 or >=11.17.0 |
| pnpm | 12.15.0 | OpenClaw `packageManager` exact version and integrity |
| uv bootstrap | 0.12.23 | Exact integration tooling selection |

The Python patch and tooling versions are integration selections, not claims
that upstream pins those exact patches. Source identities and Node archive
SHA-256 hashes are recorded in [runtime-pins.json](runtime-pins.json). The
audited sources are:

- Zenith: `f1dbab49f915d4c74b57e560aafac7e51efde373`
- Hermes: `d05095663342556788cf2a198bfa7844cc7968ab`
- OpenClaw: `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`

The SDK environment includes pytest 9.1.1, pytest-asyncio 1.4.0, OpenAI 2.54.0,
Agent Client Protocol 0.9.0, HTTPX 0.28.1, and websockets 15.0.1. Transitive
packages are pinned with hashes in `requirements-test.txt`; `requirements-test.in`
is the reviewed input. SDK imports passing does not verify native agent execution.

## Install prerequisites

From the Zenith folder, use a dedicated bootstrap environment and runtime folder
outside all Git repositories. Downloads preserve the inherited network proxy and
TLS trust. Do not disable certificate verification. Plan at least 1 GB for these
prerequisites and substantially more for both native dependency trees and builds.

Linux:

```bash
python3 -m venv "$HOME/.zenith-runtime-bootstrap"
. "$HOME/.zenith-runtime-bootstrap/bin/activate"
python -m pip install uv==0.12.23
python integrations/runtime_setup/setup.py --root "$HOME/.zenith-integration-runtimes" --install
deactivate
```

Windows PowerShell:

```powershell
py -3.12 -m venv "$env:LOCALAPPDATA\ZenithRuntimeBootstrap"
& "$env:LOCALAPPDATA\ZenithRuntimeBootstrap\Scripts\python.exe" -m pip install uv==0.12.23
$env:PATH = "$env:LOCALAPPDATA\ZenithRuntimeBootstrap\Scripts;" + $env:PATH
py -3.12 integrations/runtime_setup/setup.py --root "$env:LOCALAPPDATA\ZenithIntegrationRuntimes" --install
```

Omit `--install` to inspect pins without creating files or downloading anything.
The installer checks supported OS/architecture, available storage, ownership of
its output folder, archive hashes, exact runtime versions, SDK dependency
consistency, and real imports. Archives support Linux, Windows and macOS on x64
and ARM64; executable verification on each platform is still required. It uses
uv's managed Python downloads and the native npm lock/integrity mechanism. Node
archives are checked against the recorded official distribution hashes.

`receipt.json` contains the exact runtime paths, version pins, requirements hash,
and smoke outcome. It records native dependency installation and integration
verification as false. No credentials or model state are copied. Partial setup
fails visibly; retry the same owned folder after resolving the reported issue.
Do not point this installer at an existing unrelated environment.

## Native dependencies and baseline tests

Keep three separate environments. Zenith 0.17.3 raises its cryptography floor
to 50.0.2, but matching one library does not make the Python runtimes and full
dependency graphs interchangeable. Never combine Hermes' `uv.lock` with
Zenith's dependencies or OpenClaw's `pnpm-lock.yaml`.

Use isolated disposable copies of the pinned sources for native installs/builds;
retain the original audited copies and licenses unchanged. Check each copy's
`git rev-parse HEAD` against `runtime-pins.json` before setup, and verify tracked
source hashes afterward. Build/package-manager lifecycle scripts execute code;
use a secretless, resource-limited environment with no production state mounts.

Linux example for a dedicated build environment, after loading paths from the
successful setup receipt (adapt paths for your chosen root):

```bash
export ZENITH_INTEGRATION_ROOT="$HOME/.zenith-integration-runtimes"
export UV_PYTHON_INSTALL_DIR="$ZENITH_INTEGRATION_ROOT/python"
export PATH="$ZENITH_INTEGRATION_ROOT/node-v26.12.1-linux-x64/bin:$PATH"
```

For Hermes, use its own package manager and canonical test runner:

```bash
cd /path/to/disposable-pinned-hermes-copy
bash scripts/run_tests.sh -j 2
```

The runner uses `scripts/run-in-hermes-env` and PM's isolated test environment,
the locked project dependencies, `dev` and `test` groups, and default `all`
extras. Let PM provision this environment; do not mutate it with raw pip/uv or
substitute the lean bridge SDK environment. The ACP runtime extra must also be
enabled through Hermes' native PM configuration when testing ACP. The native
runtime has additional platform/tool-specific dependencies and external-service
requirements; the small SDK installation does not satisfy those.

For OpenClaw, use the isolated pnpm CLI and its existing frozen lock:

```bash
cd /path/to/disposable-pinned-openclaw-copy
node "$ZENITH_INTEGRATION_ROOT/node-tools/node_modules/pnpm/bin/pnpm.mjs" install --frozen-lockfile
node "$ZENITH_INTEGRATION_ROOT/node-tools/node_modules/pnpm/bin/pnpm.mjs" test
```

These native setup commands may download large dependency trees and run native
build scripts. They require a compatible host and sufficient disk; record the
actual command, environment, exit status and logs. A missing dependency or
insufficient storage is a blocker, not a passing native baseline. Keep native
accounts, memories, sessions, schedulers, configuration and secrets isolated.

## Tests, updates and rollback

```bash
python -m unittest discover -s tests -p test_runtime_setup.py -v
```

Review pin updates against each upstream manifest. Regenerate the SDK lock using
uv 0.12.23 and Python 3.14, then test a fresh external runtime folder:

```bash
uv pip compile integrations/runtime_setup/requirements-test.in --python-version 3.14 --universal --generate-hashes --only-binary :all: --output-file integrations/runtime_setup/requirements-test.txt
```

No service or startup task is registered. To roll back, stop processes you
explicitly started from this environment, inspect `receipt.json`, and remove
only its dedicated runtime/bootstrap folders. Keep native source copies and
state. Revert this additive commit to remove the setup files; Zenith's model,
installed environment, memory and deployment receipts are unaffected.

The inference adapter and native bridge remain separately approval-gated. This
setup does not imply model tool-calling compatibility or verified 24/7 operation.
