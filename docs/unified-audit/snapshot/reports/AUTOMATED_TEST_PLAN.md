# Automated acceptance and regression plan

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Evidence levels

A parser/import test verifies only that narrow property. Unit tests may use deterministic fakes for fault injection; integration tests must exercise real SQLite, process/transport boundaries and actual configured backends. End-to-end parity needs frozen reference-equivalent workloads, the unchanged selected Zenith checkpoint, recorded scopes and independent outcome checks. Passing unit tests alone never upgrades a feature to VERIFIED. Every run records repository SHA, configuration and fixture hashes, model/tokenizer/adapter hashes, platform, dependency lock, command, seed, raw timings, results and exclusions. Credentials and private conversations are excluded from public artifacts.

## Required acceptance by subsystem

| Group | Required executable gate | Primary test destinations |
| --- | --- | --- |
| G00 | Verify pinned baseline/model/tokenizer hashes, PR19 divergence and rollback backup; no original checkpoint mutation. | tests/test_platform_protection.py |
| G01 | Deny forged actors, stale MFA/grants, cross-account references and post-approval argument changes with zero side effects; preserve old DB writers. | tests/test_unified_permissions.py, tests/test_unified_migrations.py |
| G02 | Owned container/VM runs real bounded tools; reject forbidden file/network/process access, junction/symlink escapes and missing sandbox; no host fallback. | tests/test_unified_sandbox.py, tests/e2e/test_unified_execution.py |
| G03 | Actual selected Zenith checkpoint completes frozen multi-step workflows with valid schemas, error recovery, budgets, attribution and cancellation; malformed calls have no effects. | tests/test_unified_model_turns.py, tests/integration/test_unified_autonomy.py |
| G04 | Real HTTP/WS admission, replay, ownership, lease fencing and restart/cancel; uncertain non-idempotent writes reconcile instead of replay. | tests/integration/test_unified_gateway.py, tests/e2e/test_unified_recovery.py |
| G05 | Account/project recall, deletion/TTL, provenance, bounded context, compression checkpoint/recovery and retrieval relevance on frozen labels; no private/shared-corpus crossover. | tests/test_unified_memory.py, tests/integration/test_unified_compression.py |
| G07 | Pinned manifest/schema/protocol negotiation, actual isolated invocation, tool/resource discovery, cancellation, auth/revocation and upgrade reapproval; malformed packages fail closed. | tests/test_unified_plugin_integrity.py, tests/integration/test_unified_mcp.py |
| G06 | Generate a real candidate from consented successful/failed traces, test on independent fixtures, review/activate/version/rollback; optional continued training preserves parent and retained quality. | tests/test_unified_skill_learning.py, tests/integration/test_unified_learning_cycle.py |
| G08 | Real supervisor/child goal completion, isolated workspaces, strict-subset grants, collective budgets, cancel/steer, blocked-input/review handoff and recovery. | tests/integration/test_unified_multi_agent.py |
| G09 | Each separately inventoried service proves owned-account pairing, valid/invalid signatures, replay rejection, text/media/thread semantics and uncertain-send reconciliation; no test double counts as live service verification. | tests/integration/test_unified_channels.py, tests/e2e/test_unified_channel_accounts.py |
| G11 | Actual isolated browser/VM/owned SSH endpoint, all-subresource egress checks, private-profile exclusion, approval-bound writes, cancellation and cleanup; missing backend is unavailable. | tests/e2e/test_unified_browser.py, tests/e2e/test_unified_desktop.py, tests/e2e/test_unified_remote_hosts.py |
| G13 | Exact account-visible model IDs, local-default/privacy routing, errors/failover and actual least-privilege owned API/database/host operations; unsupported/restricted models unavailable. | tests/integration/test_unified_providers.py, tests/e2e/test_unified_infrastructure.py |
| G10 | Durable UTC/cron+timezone jobs with tested DST/misfire/overlap policy, standing-authority expiry, event dedup and restart recovery. | tests/integration/test_unified_scheduler.py |
| G12 | Real licensed compatible backends with bounded files, OCR/STT/TTS/vision/media fixtures and declared failure/unsupported formats; preserve text-only installation. | tests/e2e/test_unified_multimodal.py |
| G14 | Real target-OS builds, login/task/approval/reconnect/accessibility/media workflows and identity/model attribution; no native-client claim from Linux-only unit tests. | tests/e2e/test_unified_ui.py, clients/tui/tests/session.test.ts, clients/desktop/tests/gateway.test.ts |
| G15 | Frozen paired reference/Zenith tests, security/retention/performance regressions, Windows/Linux CPU and optional GPU/remote/container/companion jobs, model-hash and rollback drills; publish only actual results. | tests/test_unified_installation.py, tests/e2e/test_unified_acceptance.py |

Additional per-integration assertions are specified in [the full matrix](MASTER_FEATURE_PARITY_MATRIX.csv) and [file plan](FILE_BY_FILE_IMPLEMENTATION_PLAN.md). Each channel tests real inbound/outbound protocol, signature/replay, identity mapping, threading, edit/delete/reactions/media where supported, payload limits, retry/reconciliation and revocation. Each provider tests account-visible discovery, exact IDs, modalities, tool schema, streaming/cancellation and error/failover attribution. Unconfigured external services remain BLOCKED; a fake adapter is not a production pass.

## Workloads and gates

1. Baseline/regression: fresh main suite plus unchanged native checkpoint inference. Candidate must preserve existing public APIs, data, login and local installation. Compare on identical model and hardware, not stronger replacement weights.
2. Deterministic agent tasks: owned temporary Git repo (inspect→patch→test→verify), SQLite query→chart artifact, scoped retrieval→answer/source check and failure→correction. Use independent file/db assertions and real bounded tools; report model selection, budget and complete task outcomes.
3. Memory: synthetic two-account/project corpora, duplicate/expired/deleted facts, relevant/irrelevant passages, summaries and restart; recall@k/MRR plus zero cross-account returned rows. Do not train on heldout queries.
4. Skills/learning: successful/failed/rescued trajectories, inactive candidate generation, isolated tests, poisoned skill rejection, human review/version activation, regression and rollback; compare heldout task success and unnecessary tool/token cost.
5. Security: all denial cases in the threat model, prompt-injection fixture corpus, approval mutation/replay, outbound canary endpoints, forbidden host-file probes, audit failure, scope revocation under load and emergency shutdown. Require zero prohibited side effects in these fixtures; do not claim universal safety.
6. Persistence/recovery: kill worker at each task transition, SQLite busy/disk-full/failure injection, WAL-consistent backup, lease fencing, unknown external writes, duplicate callback/outbox replay and mixed old/new schema writer behavior.
7. Multi-agent: disjoint workspaces, shared bounded information, conflicting patches, scoped children, supervisor cancellation and bounded parallelism; shared local model uses serialization until tested otherwise.
8. Media/clients: real licensed fixtures with OCR accuracy, transcription WER, actual audio playback/file validity, image/video pipeline source attribution and missing-dependency behavior; OS-specific UI permission tests on actual supported systems. Text-only installation must still work.
9. Knowledge/reasoning/coding: freeze appropriately licensed GSM8K, HumanEval+ and selected SWE-bench fixtures with contamination/provenance notes; sandbox executable code tests. These benchmarks are planned, not run. A small selected model may fail; report failure rather than silently swapping it.
10. Performance: monotonic TTFT/full latency, tokens/s, input/output/tool tokens, RSS/VRAM/GPU, errors, provider spend, concurrency and successful-task cost. Warm/cold runs and output lengths separated; no speedup claim from the current two-probe sample.

## Promotion and publication

Pin fixture revisions and hashes before tuning. Separate train/replay/development/test partitions and preserve their provenance. Candidate skill/code/adapter evaluation has separate quality and authorization gates. Failed gates remain failed; exceptions, if allowed, must be explicitly recorded and cannot relabel a score. No automatic adapter promotion. Independently review code, migrations, licenses, security and model-quality evidence; publication is separate from running local tests.
