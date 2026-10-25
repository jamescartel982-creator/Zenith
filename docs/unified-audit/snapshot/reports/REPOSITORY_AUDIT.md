# Pinned-source architecture audit

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Review boundary and preservation

The latest mission expands the approved OpenClaw-only scope to Hermes. Its Phase 1 explicitly says not to modify Zenith before this audit is completed and approved. Previous blanket approvals and the separate OpenClaw pilot do not override that new boundary. No application code, README, deployment, model, active profile, checkpoint registration or PR state was changed for this audit.

The existing OpenClaw clone was reused at its verified immutable commit; Hermes and current Zenith main were freshly cloned. OpenClaw's pin is the same snapshot as the earlier source audit, not a claim to include every subsequent upstream commit. Main branches can move: acceptance must name exact reference commits and include a delta audit before later pin upgrades. The code inventory hashes every tracked file in all four views. Manual semantic tracing covers critical owners; whole-tree hashing/import indexing is **not** line-by-line manual review or a complete resolved call graph.

| View | Commit / branch | Tracked files | Python AST modules | Runtime / license |
| --- | --- | --- | --- | --- |
| OpenClaw | 2f5727b9c61c2ba9dccc3c880d9115f02cb8652f / detached | 59647 | 64 | 2026.10.7; Node >=24.22.1 <25 or >=26.12.1; pnpm 12.15.0; MIT |
| Hermes | d05095663342556788cf2a198bfa7844cc7968ab / main | 21255 | 10208 | Package version 0.0.0; PM Python 3.14; Node >=26; MIT, Nous Research 2025 |
| Zenith main | e6963d9c6f45c196ae2e301819ae1ae093b35c41 / main | 375 | 128 | 0.15.0; Python >=3.10; Windows/Linux CI 3.10/3.12; Apache-2.0 |
| Zenith PR19 | 44d55d23cb946254a4a718a35a7c5432003cc01b / feature/openclaw-platform | 426 | 148 | Unmerged draft supervised task pilot; same trained model and installer |

The original development checkout is separately preserved at PR #18 commit `ac989d869f2c2b961003684dc6ee7843d01d08da` (optional reasoning). PR #18 and PR #19 remain open/unmerged; their overlapping config/core/execution/planning owners need deliberate reconciliation after approval. Current main must not be described as already containing either PR.

## Inspection method and evidence

`evidence/*-source-index.jsonl.gz` contains path, byte length, SHA-256 and static import/export/function anchors. Python files parsed under the host's Python 3.12 with zero reported parse errors; parsing is not runtime compatibility. TS/JS uses regex indexing, not a compiler-verified module graph. Test-named paths are filename counts, not executed test cases. The source manifest, plugin manifests, tool registration sites, skill packages, English Hermes docs and OpenClaw docs are cross-indexed in the master matrix. Dynamic/table-driven registrations remain identified as expressions where their names cannot safely be resolved statically. Nothing from either reference runtime was imported to discover its capabilities.

| Surface | OpenClaw | Hermes | Interpretation |
| --- | --- | --- | --- |
| Plugin manifest files | 184 | 108 | Declarations; not all are channels or independent capabilities |
| SKILL.md files | 128 | 211 | Instruction/resource packages, including optional/fixture/vendor paths; not neural weights |
| Indexed doc pages | 1398 | 457 | Coverage anchors; overlap/overview pages are not unique features |

The matrix has 3672 labeled coverage records. It preserves overlaps between core behavior, manifests, concrete integration identities, tool declarations, skills, documentation and external catalog entries rather than inflating a unique-capability count. 827 Hermes external catalog references are individually tracked and blocked on external source/license review; their implementation is outside the three repos and has not been audited here.

Evidence lives in `repositories.json`, `dependency-declarations.json`, `license-inventory.json`, `plugin-manifests.json`, `tool-registrations.json`, `documentation-index.json`, `skill-packages.json` and the compressed source indexes. These are source declarations, not a resolved installed SBOM or evidence of service access.

## Traced architecture boundaries

OpenClaw: CLI → gateway ownership/database admission → HTTP/WebSocket handshake → scoped request dispatch → admitted run → agent tool loop → per-turn authority gate → plugin/sandbox effect → event/result persistence. Its protocol frames are its own versioned RPC, not MCP. Its memory engine is under `extensions/memory-core`, and its current cron store is SQLite-backed. See [OpenClaw detail](OPENCLAW_REVERSE_ENGINEERING.md).

Hermes: CLI/gateway/TUI → `AIAgent` facade → durable turn admission → context/request construction → response normalization → tool rounds → sequential/parallel executor → registry/approval/backend → finalization/persistence. Memory providers, skill operations and curator hooks are separate owners; learning artifacts are not new foundation weights. See [Hermes detail](HERMES_REVERSE_ENGINEERING.md).

Zenith: current Agent/context/provider lock and SQLite owners remain authoritative. PR19 adds a supervised queue, fixed diagnostic approvals/events and metadata HMAC history; it does not generate autonomous model tool calls, execute general code, run subagents or host channels. See [current Zenith architecture](ZENITH_CURRENT_ARCHITECTURE.md).

## Runtime and trust compatibility findings

S: Hermes top-level `requires-python` is >=3.11,<3.15, but `.python-version`, PM's project/lock and Python-version markers target the managed 3.14 runtime. Its desktop/root Node engines require >=26. Many app dependencies are only declared for >=3.14; a bare import/install into Zenith 3.12 is not a supported reuse strategy. Sources: [pyproject.toml:15](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/pyproject.toml#L15), [pm/pyproject.toml:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/pm/pyproject.toml#L1), [.python-version:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/.python-version#L1), [package.json:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/package.json#L1), [apps/desktop/package.json:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/apps/desktop/package.json#L1).

S: Hermes `model_tools.py` discovers tools and plugins at import; its plugin loader can execute Python in the agent process. Default terminal configuration is local host execution. These are deliberate personal-agent trust assumptions, not proof of an exploit. Zenith's multi-account server and requested untrusted-execution boundary require a stricter broker/worker design. Sources: [model_tools.py:150](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/model_tools.py#L150), [hermes_cli/plugins.py:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/hermes_cli/plugins.py#L1), [hermes_cli/config_defaults.py:298](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/hermes_cli/config_defaults.py#L298), [SECURITY.md:1](https://github.com/NousResearch/hermes-agent/blob/d05095663342556788cf2a198bfa7844cc7968ab/SECURITY.md#L1).

S: OpenClaw's sandbox resolver defaults to off, and some compatibility HTTP shared-secret endpoints intentionally use full operator scope. Do not adopt those defaults as Zenith's account/admin model. Sources: [src/agents/sandbox/config.ts:233](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/agents/sandbox/config.ts#L233), [src/gateway/http-endpoint-helpers.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/gateway/http-endpoint-helpers.ts#L1).

## Executable baseline and limits

M: Fresh cloned-main suite ran **243 tests, 242 passed, one skipped, 33.364 s**. The existing trained HF/LoRA checkpoint loaded offline; arithmetic/geography probes returned `4` and `Paris` on direct and routed paths. Adapter/profile hash checks passed. These two probes do not establish broad intelligence, agent competence, security parity or faster performance.

Earlier PR19 evidence is reused at its unchanged commit: 277 local tests (one skip), seven remote Windows/Linux/container checks plus the diagnostic watch passed. Its three-pair CPU queued-chat median was slower than legacy chat (9855.643 vs 6423.591 ms); no speedup is claimed. Reference runtimes, external channels, native companion apps, Docker/VM execution and GPU benchmarks were not run in this audit. Host Python 3.12/Node 24.19.0 do not satisfy the references' full supported runtime requirements; no service credentials are configured in the managed environment.

No new unified parity is VERIFIED. Baseline measurements, source declarations and proposed acceptance tests are separated throughout this package.
