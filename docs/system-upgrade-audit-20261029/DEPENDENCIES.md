# Dependency, license and platform assessment

## Current environments

| Component | Declared/runtime requirements | Assessment |
| --- | --- | --- |
| Root Zenith | Python >=3.10; FastAPI, Uvicorn, requests, urllib3, dotenv, Argon2, pyotp, cryptography | Current root Python 3.12.14; 81 installed distributions including Zenith; package compatibility check passed. |
| Local/train extras | Torch >=2.6,<3; Transformers >=5.10.4,<5.11; PEFT >=0.18.1,<0.19; Accelerate >=1,<2; dataset extras separately | Selected CPU inference versions loaded successfully. GPU/QLoRA not verified. Root ranges are not a complete platform lock. |
| Bridge | Python >=3.12,<3.13; zenith-local 0.17.4, HTTPX, JSON Schema; native websockets 15.0.1 | Separate uv lock; preserve root Python-3.10 compatibility and optional packaging boundary. |
| Inference service | Python >=3.12,<3.13; bridge + selected local extra; test OpenAI SDK 2.54.0 | Frozen platform-aware lock for Linux x64, Windows x64, macOS ARM64. Native Intel macOS Torch unsupported in this setup. |
| Trading service | Python >=3.12,<3.13; bridge; TradingAgents exact Git pin | Separate frozen environment. Native graph is not a broker or a complete paper-accounting/backtest service. |
| Hermes native | Python >=3.14,<3.15, pinned 3.14.8; Node >=26; native uv.lock | Do not merge into root Python environment. Approved compatibility copy is separate and chat-only. |
| OpenClaw native | Node >=24.22.1 <25 or >=26.12.1; recorded Node 26.12.1, pnpm 12.15.0 | Preserve package manager integrity hash and native pnpm lock. Builds need more disk/RAM than this workspace has free. |
| Runtime bootstrap/test SDKs | uv 0.12.23, npm 11.17.0, hash-checked platform archives and requirements | Existing runtime-pins.json records original audit pins; its Zenith baseline field is historical, not current main. |

The Hermes, OpenClaw and TradingAgents pins are recorded in AUDIT.md and freshly
checked in upstream-pins.json. Test tooling added during this audit was isolated
under temporary directories; the installed root environment and manifests were
not updated. Root/service unit suites used explicit local package paths and a
temporary JSON Schema dependency, not a claim of a fresh full native installation.

## Actual advisory and compatibility results

The 80 installed non-Zenith distributions were captured before adding audit
tooling in [root-installed.txt](root-installed.txt). pip-audit 2.9.0 ran in a
separate temporary tool environment with no advisory exclusions:

- 79 dependencies: no known advisories returned.
- Exact `torch==2.14.1+cpu`: skipped because PyPI could not locate that version.
- Exit code was zero despite that skip. This is a demonstrated audit-coverage
  gap, not proof of a Torch vulnerability or a complete clean bill of health.
- A separate query for upstream `torch==2.14.1` returned no known advisories;
  [torch-upstream-advisories.json](torch-upstream-advisories.json) is supplemental
  and does not establish binary/vendor-wheel equivalence or eliminate the skip.
- `uv pip check --python .venv/bin/python`: all installed packages compatible.
  Compatibility does not establish vulnerability freedom.

[dependency-advisories.json](dependency-advisories.json) preserves the full scan,
including its skip_reason. No integration/Node tree was rescanned here. Current
security workflow path filters cover root requirements/pyproject, not every
integration lock; Dependabot currently lists root pip and GitHub Actions.
Add explicit coverage for each isolated environment, native JS dependency tree,
vendor build provenance and optional future subsystem. Fail a completeness gate
when a dependency is unscanned unless a reviewed, attributable alternate audit
provides coverage. Never silently ignore an advisory or strip local versions and
pretend the exact binary was assessed.

## Proposed optional additions

These are candidates for compatibility spikes, **not pinned or installed by this
audit**. Resolve exact versions/hashes and licenses only when that PR is tested.

| Need | Candidate component | Admission conditions |
| --- | --- | --- |
| Private semantic retrieval | Optional reviewed embedding model / sentence-transformers or a local embedding service | License and revision verified; CPU/RAM measured; vector index owner/deletion tests; no tokenizer changes. Start with existing FTS5. |
| Repository parsers | Python ast; optional tree-sitter/language-specific parsers/LSPs | Untrusted parse limits, per-language license/toolchain inventory and platform acceptance. |
| MCP | Official Python MCP SDK in isolated service | Supported protocol/version verified against official conformance; auth/transport/isolation tests; no root import requirement. |
| Browser | Playwright in independent service/container | Browser binary/version licensing, actual browser tests, no host credential profile, restricted egress. |
| Documents | Optional pypdf, python-docx/openpyxl/python-pptx, safe XML handling | Parse in bounded isolation; no macros/formula execution/external entities; malicious fixtures required. |
| Speech/vision/media | Approved local STT/TTS/VLM/OCR; FFmpeg where licensed | Separate model artifacts and rights; actual quality/resource measurements; consent/retention; preserve text-only path. |
| Telemetry | Optional psutil, NVIDIA NVML binding, OpenTelemetry | Bounded/private metrics; N/A on absent sensors; GPU evidence needs actual hardware. |
| GPU/quantized training | Optional validated inference server or bitsandbytes/QLoRA | Linux/CUDA/model compatibility spike; immutable original weights; numerical/quality/retention tests and separately reviewed artifacts. |
| Malware behavior | Disposable VM/microVM service | Dedicated isolation review, sample policy, no host shares, no production credentials, measured containment. Container-only Python sandbox is insufficient. |

Avoid introducing these dependencies into the default installation before a
working backend and optional-import tests exist. Locked toolchains/packages
should be materialized from reviewed offline artifacts in untrusted execution;
do not let a model run arbitrary host pip/npm/curl installation commands.

## Licenses and rights

Zenith's root and existing sidecar packages declare Apache-2.0. The exact pinned
Hermes LICENSE is MIT (Nous Research); OpenClaw LICENSE is MIT (OpenClaw Foundation);
TradingAgents LICENSE is Apache-2.0. Fresh license headers/hashes are recorded in
[licenses.json](licenses.json). Retain their licenses/notices and inspect each
third-party inventory when redistributing a build. TradingAgents'
license and notices stay with its pinned source/distribution. Root
license does not relicense dependencies, weights, voices, market feeds or datasets.

The current curriculum enforces a limited accepted-license set, source revisions,
explicit training approval and grouped split isolation. A reference URL or model
catalog entry is not permission to copy/train/distribute every referenced file.
Provider outputs must remain excluded from training unless specific terms and
permissions permit it. Preserve upstream identifiers and attribution; renaming
source/model IDs does not remove license obligations. New dependency/model/feed
licenses and any redistribution restrictions must be recorded in each actual PR.

## Infrastructure blockers

This executor has two CPU quota, 8 GiB memory and no GPU. Initial disk headroom
was about 158 MiB; a fresh native build, model duplication or training corpus dump
is inappropriate here. No active cloud/broker/provider identity was supplied by
the execution environment. Persistent hosting, extended soak, full native parity,
GPU profiling, real desktop sessions, live messaging and external model access
require separately configured environments. Do not invent substitute credentials
or treat a transient workspace as permanent deployment.
