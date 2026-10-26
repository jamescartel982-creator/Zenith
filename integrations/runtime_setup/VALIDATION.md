# Prerequisite validation — 2026-10-26

Tested on Linux x86-64 in a dedicated external runtime folder, using the
existing Zenith source baseline `f1dbab49f915d4c74b57e560aafac7e51efde373`.

| Check | Actual result |
| --- | --- |
| Node official archive SHA-256 | Matched recorded Linux x64 hash |
| Node executable | 26.12.1 |
| npm executable | 11.17.0 |
| pnpm executable | 12.15.0 |
| pnpm integrity | Matched audited OpenClaw `packageManager` SHA-512 |
| Managed Python executable | 3.14.8 |
| uv tooling | 0.12.23 |
| Hash-checked SDK installation | 24 compatible installed distributions |
| Real imports | pytest, pytest-asyncio, OpenAI, ACP, HTTPX, websockets passed |
| Isolated SDK pytest run | 12 passed, six subtests passed, 0.08 seconds |
| Full Zenith unittest suite | 320 run; 319 passed, one skipped; 46.611 seconds |
| Existing Zenith environment | `pip check`: No broken requirements found |
| Pinned Hermes/OpenClaw audited sources | Both Git working trees remained clean |
| Repeat prerequisite installation | Passed with the final universal SDK lock |
| Real-install CI (initial PR revision) | Windows and Linux passed; run 40269625467 |

The final SDK lock SHA-256 is
`5e3acf71becb413a836c13a0d3830a07f4b30f060c9ab6ed60721438fa2225e5`.
The universal lock includes Windows-only dependency markers. The installer
receipts and package-manager lock remain in the dedicated external runtime
folder rather than application state or source control.

Only about 506 MiB disk space remained after the 521 MiB prerequisite
installation. The complete Hermes/OpenClaw dependency trees, original upstream
test suites, builds, gateway operation, and cross-runtime inference were not
run here. These remain blocked pending sufficient isolated storage and native
environments. A separate CI workflow exercises real prerequisite installation
on Windows and Linux. Both jobs passed on initial PR revision `6f53c965`; final
revision results must be inspected independently. The initial existing Zenith
source-consistency check detected the requested README change; the source
release manifest was regenerated to record the edit and all additive files.

No inference adapter, bridge, service, automatic startup, model update, training
or deployment was enabled by this change. Native parity and 24/7 availability
remain unverified. The original architecture review's inference-adapter
approval boundary remains in place.
