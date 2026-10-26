# License, dependency and platform compatibility

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

OpenClaw root license is MIT (OpenClaw Foundation, 2026); Hermes root license is MIT (Nous Research, 2025). Zenith is Apache-2.0. MIT code can generally be incorporated while preserving the copyright/permission notices; this audit is not legal clearance for every transitive asset or plugin. [License inventory](../evidence/license-inventory.json) records source license/notice files; [dependency declarations](../evidence/dependency-declarations.json) records declared roots/workspaces, not a resolved transitive SBOM. Public root license texts are included in the evidence folder. No upstream source code, assets or model weights were copied into Zenith by this audit.

Before copying or adapting any implementation, pin the exact files/commit, retain required MIT notices and applicable third-party notices, review bundled fonts/media/vendor libraries, record provenance in Zenith NOTICE/THIRD_PARTY_NOTICES, and review resolved optional dependencies, native binaries, model and dataset terms. Preserve attribution even if symbols are renamed. Reimplementing a compatible protocol does not grant access to a proprietary service or authorize reuse of its branding, credentials, outputs or training data. Catalog-only packages (827 references) remain blocked until their own source and licenses are reviewed.

| Component | Pinned runtime / dependency constraint | Compatibility decision |
| --- | --- | --- |
| Zenith main | Current Python local install; preserved CPU Transformers/PEFT adapter path | Keep core and text-only path; optional capabilities must not force incompatible dependency upgrades |
| OpenClaw | Node >=24.22.1 <25 or >=26.12.1; pnpm12.15.0; SQLite/native and platform packages | Current Node24.19.0 is unsupported; source audit only, no upstream runtime verified |
| Hermes root/PM | Bridge requires-python >=3.11,<3.15; managed PM >=3.14,<3.15; .python-version 3.14; Node>=26 | Python3.12 AST parsing is not runtime support. Independent managed environment needed for reference execution |
| Hermes dependency overlap | Most root dependency markers >=3.14; cryptography50.0.2 versus Zenith>=44,<48 | Do not merge requirements wholesale; implement native contracts or isolate reviewed workers |
| Hermes desktop | Electron and Node>=26; platform packaging/signing policies differ | No implicit Linux desktop release support from build scripts; actual target OS acceptance needed |
| Optional services/models | Account-visible APIs, credentials, API terms, retirement and quota policies | Unavailable/restricted models remain unavailable; discover exact authorized IDs, do not fabricate family availability |
| Third-party packages/catalog | Remote referenced source not necessarily vendored or covered by root MIT | BLOCKED pending provenance, lock resolution, security and license review |
| GPU/mobile/browser | Hardware, OS permissions, sandbox and native package constraints | Keep optional; report unsupported or untested combinations explicitly |

Hermes supported-platform policy includes macOS arm64 desktop, Windows10/11 CLI and Windows11 22H2+ MSIX, Linux/WSL2 CLI and Docker; Nix/Android Termux aarch64 are best-effort. Upstream policy is not evidence those platforms work in Zenith. Current host has no demonstrated GPU and lacks supported reference Node versions. No automatic dependency installation or upstream setup script was executed.
