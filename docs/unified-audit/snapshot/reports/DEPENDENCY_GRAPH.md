# Dependency graph

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

```mermaid
graph TD
  G00["G00: Baseline, approval and existing-PR reconciliation"]
  G01["G01: Identity, policy, schemas, audit and secrets"]
  G00 --> G01
  G02["G02: Isolated execution, files, shell, Git and egress"]
  G01 --> G02
  G03["G03: Typed model turns and autonomous runtime"]
  G01 --> G03
  G02 --> G03
  G04["G04: Durable sessions, tasks, events, HTTP/WebSocket/CLI"]
  G03 --> G04
  G05["G05: Persistent scoped memory and context compression"]
  G01 --> G05
  G04 --> G05
  G07["G07: Plugin/skill packages, MCP and dynamic discovery"]
  G01 --> G07
  G02 --> G07
  G04 --> G07
  G06["G06: Reviewed learning, trajectories, skill candidates and workflow discovery"]
  G03 --> G06
  G05 --> G06
  G08["G08: Supervisor, specialist children and shared task graph"]
  G03 --> G08
  G04 --> G08
  G07 --> G08
  G09["G09: Channels, identity routing, notifications and delivery"]
  G01 --> G09
  G04 --> G09
  G07 --> G09
  G11["G11: Browser, computer, remote environments and credential vault"]
  G02 --> G11
  G04 --> G11
  G07 --> G11
  G13["G13: Provider and infrastructure connectors"]
  G01 --> G13
  G03 --> G13
  G07 --> G13
  G10["G10: Schedules, heartbeat, triggers and event workflows"]
  G04 --> G10
  G08 --> G10
  G09 --> G10
  G12["G12: Multimodal documents, images, audio, video and voice"]
  G03 --> G12
  G07 --> G12
  G09 --> G12
  G11 --> G12
  G14["G14: CLI/TUI/web/desktop/mobile applications"]
  G04 --> G14
  G08 --> G14
  G09 --> G14
  G12 --> G14
  G15["G15: Packaging, deployment, benchmarks and acceptance release"]
  G04 --> G15
  G06 --> G15
  G08 --> G15
  G10 --> G15
  G11 --> G15
  G12 --> G15
  G13 --> G15
  G14 --> G15
```

| Order | Group | Prerequisites | Acceptance gate |
| --- | --- | --- | --- |
| 1 | G00 | Expanded audit approval | Verify pinned baseline/model/tokenizer hashes, PR19 divergence and rollback backup; no original checkpoint mutation. |
| 2 | G01 | G00 | Deny forged actors, stale MFA/grants, cross-account references and post-approval argument changes with zero side effects; preserve old DB writers. |
| 3 | G02 | G01 | Owned container/VM runs real bounded tools; reject forbidden file/network/process access, junction/symlink escapes and missing sandbox; no host fallback. |
| 4 | G03 | G01, G02 | Actual selected Zenith checkpoint completes frozen multi-step workflows with valid schemas, error recovery, budgets, attribution and cancellation; malformed calls have no effects. |
| 5 | G04 | G03 | Real HTTP/WS admission, replay, ownership, lease fencing and restart/cancel; uncertain non-idempotent writes reconcile instead of replay. |
| 6 | G05 | G01, G04 | Account/project recall, deletion/TTL, provenance, bounded context, compression checkpoint/recovery and retrieval relevance on frozen labels; no private/shared-corpus crossover. |
| 7 | G07 | G01, G02, G04 | Pinned manifest/schema/protocol negotiation, actual isolated invocation, tool/resource discovery, cancellation, auth/revocation and upgrade reapproval; malformed packages fail closed. |
| 8 | G06 | G03, G05 | Generate a real candidate from consented successful/failed traces, test on independent fixtures, review/activate/version/rollback; optional continued training preserves parent and retained quality. |
| 9 | G08 | G03, G04, G07 | Real supervisor/child goal completion, isolated workspaces, strict-subset grants, collective budgets, cancel/steer, blocked-input/review handoff and recovery. |
| 10 | G09 | G01, G04, G07 | Each separately inventoried service proves owned-account pairing, valid/invalid signatures, replay rejection, text/media/thread semantics and uncertain-send reconciliation; no test double counts as live service verification. |
| 11 | G11 | G02, G04, G07 | Actual isolated browser/VM/owned SSH endpoint, all-subresource egress checks, private-profile exclusion, approval-bound writes, cancellation and cleanup; missing backend is unavailable. |
| 12 | G13 | G01, G03, G07 | Exact account-visible model IDs, local-default/privacy routing, errors/failover and actual least-privilege owned API/database/host operations; unsupported/restricted models unavailable. |
| 13 | G10 | G04, G08, G09 | Durable UTC/cron+timezone jobs with tested DST/misfire/overlap policy, standing-authority expiry, event dedup and restart recovery. |
| 14 | G12 | G03, G07, G09, G11 | Real licensed compatible backends with bounded files, OCR/STT/TTS/vision/media fixtures and declared failure/unsupported formats; preserve text-only installation. |
| 15 | G14 | G04, G08, G09, G12 | Real target-OS builds, login/task/approval/reconnect/accessibility/media workflows and identity/model attribution; no native-client claim from Linux-only unit tests. |
| 16 | G15 | G04, G06, G08, G10, G11, G12, G13, G14 | Frozen paired reference/Zenith tests, security/retention/performance regressions, Windows/Linux CPU and optional GPU/remote/container/companion jobs, model-hash and rollback drills; publish only actual results. |

The graph is acyclic. Logical ordering does not require a monolithic release. Shared policy, actor identities, schemas and isolation must pass before any effectful tool. Gateways and adapters consume one engine and store. Channel-specific work may proceed independently after shared contracts pass; it cannot bypass their gates. Finish each small pull request with tests, documentation, evidence and rollback, then review before enabling it. No calendar estimate or guaranteed parity date is justified by the present audit.
