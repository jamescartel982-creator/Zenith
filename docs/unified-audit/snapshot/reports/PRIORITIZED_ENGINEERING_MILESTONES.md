# Reviewable engineering milestones

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

Each group below is a milestone with one or more small PRs; large integration families must be split per adapter/transport. Do not generate every planned file in a single commit. All capabilities remain disabled until their actual acceptance gate passes on a named environment. Preserve earlier branches and review PR18/19 before choosing a base.

| Milestone | Scope | Depends on | Exit / review evidence |
| --- | --- | --- | --- |
| G00 | Baseline, approval and existing-PR reconciliation | Expanded audit approval | Verify pinned baseline/model/tokenizer hashes, PR19 divergence and rollback backup; no original checkpoint mutation. |
| G01 | Identity, policy, schemas, audit and secrets | G00 | Deny forged actors, stale MFA/grants, cross-account references and post-approval argument changes with zero side effects; preserve old DB writers. |
| G02 | Isolated execution, files, shell, Git and egress | G01 | Owned container/VM runs real bounded tools; reject forbidden file/network/process access, junction/symlink escapes and missing sandbox; no host fallback. |
| G03 | Typed model turns and autonomous runtime | G01, G02 | Actual selected Zenith checkpoint completes frozen multi-step workflows with valid schemas, error recovery, budgets, attribution and cancellation; malformed calls have no effects. |
| G04 | Durable sessions, tasks, events, HTTP/WebSocket/CLI | G03 | Real HTTP/WS admission, replay, ownership, lease fencing and restart/cancel; uncertain non-idempotent writes reconcile instead of replay. |
| G05 | Persistent scoped memory and context compression | G01, G04 | Account/project recall, deletion/TTL, provenance, bounded context, compression checkpoint/recovery and retrieval relevance on frozen labels; no private/shared-corpus crossover. |
| G07 | Plugin/skill packages, MCP and dynamic discovery | G01, G02, G04 | Pinned manifest/schema/protocol negotiation, actual isolated invocation, tool/resource discovery, cancellation, auth/revocation and upgrade reapproval; malformed packages fail closed. |
| G06 | Reviewed learning, trajectories, skill candidates and workflow discovery | G03, G05 | Generate a real candidate from consented successful/failed traces, test on independent fixtures, review/activate/version/rollback; optional continued training preserves parent and retained quality. |
| G08 | Supervisor, specialist children and shared task graph | G03, G04, G07 | Real supervisor/child goal completion, isolated workspaces, strict-subset grants, collective budgets, cancel/steer, blocked-input/review handoff and recovery. |
| G09 | Channels, identity routing, notifications and delivery | G01, G04, G07 | Each separately inventoried service proves owned-account pairing, valid/invalid signatures, replay rejection, text/media/thread semantics and uncertain-send reconciliation; no test double counts as live service verification. |
| G11 | Browser, computer, remote environments and credential vault | G02, G04, G07 | Actual isolated browser/VM/owned SSH endpoint, all-subresource egress checks, private-profile exclusion, approval-bound writes, cancellation and cleanup; missing backend is unavailable. |
| G13 | Provider and infrastructure connectors | G01, G03, G07 | Exact account-visible model IDs, local-default/privacy routing, errors/failover and actual least-privilege owned API/database/host operations; unsupported/restricted models unavailable. |
| G10 | Schedules, heartbeat, triggers and event workflows | G04, G08, G09 | Durable UTC/cron+timezone jobs with tested DST/misfire/overlap policy, standing-authority expiry, event dedup and restart recovery. |
| G12 | Multimodal documents, images, audio, video and voice | G03, G07, G09, G11 | Real licensed compatible backends with bounded files, OCR/STT/TTS/vision/media fixtures and declared failure/unsupported formats; preserve text-only installation. |
| G14 | CLI/TUI/web/desktop/mobile applications | G04, G08, G09, G12 | Real target-OS builds, login/task/approval/reconnect/accessibility/media workflows and identity/model attribution; no native-client claim from Linux-only unit tests. |
| G15 | Packaging, deployment, benchmarks and acceptance release | G04, G06, G08, G10, G11, G12, G13, G14 | Frozen paired reference/Zenith tests, security/retention/performance regressions, Windows/Linux CPU and optional GPU/remote/container/companion jobs, model-hash and rollback drills; publish only actual results. |

First implementation review: reconcile existing PR ownership without merging silently; extend policy/identity/migrations and add isolated execution; then the first typed tool loop must complete a bounded real task with the current Zenith checkpoint. If its tool-use quality is insufficient, report the measured limitation and separately propose controlled compatible training. Do not substitute a stronger model while calling the result Zenith-native parity.

Service-credential work, mobile signing, desktop OS access, hardware-dependent media, external catalog package provenance and independent reference runtimes form explicit blocker queues. Each blocked matrix row needs a maintainer decision: supply prerequisites, approve an alternative, or document a scoped exclusion. No feature may disappear from the matrix merely because it is difficult. A deadline cannot be estimated credibly before these prerequisites and early model/task measurements are resolved.

Every PR description must state the concrete behavior, evidence, security boundary, source/license attribution, exact default-off activation, migration/rollback and known limitations. `IMPLEMENTED` after code review is distinct from `VERIFIED` after integration acceptance. Overall parity remains unclaimed until all applicable contracts pass or exclusions are explicitly approved.
