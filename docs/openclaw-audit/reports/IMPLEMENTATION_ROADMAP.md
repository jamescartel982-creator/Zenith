# Implementation roadmap and review boundary

**Audit date:** 2026-10-25 UTC. **OpenClaw:** `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. **Zenith main:** `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. This is an audit/design deliverable; no Zenith implementation changes are authorized in this delivery.

**Evidence labels:** S = source-verified at the pinned commit; M = measured here; D = upstream documentation/policy claim; P = proposed design; H = hypothesis requiring implementation or experiment. Source inspection does not establish successful live execution.

## Current delivery state

**Audit and design only. Implementation has not started.** Original Zenith workspace, deployed profile, trained adapter and tokenizer were preserved. OpenClaw source was inspected at a fixed commit without installing/executing its dependency graph. Current Zenith main is 0.15.0; unmerged PR #18's bounded reasoning changes are not treated as main. Do not merge that PR, promote failed-gate adapters or deploy anything as part of this audit.

The user explicitly requested approval after audit/design. That phase boundary takes precedence over earlier blanket approval elsewhere in the conversation. This delivery makes the proposed work concrete and reviewable; the next implementation step awaits approval of scope, not another audit of the same files.

## Dependency-ordered milestones (P)

These are small independently reviewable changes/PRs, not one uncontrolled platform rewrite. Runtime exposure is gated until the applicable storage/policy/isolation dependencies are complete; milestone order can interleave metadata-only work but cannot bypass those gates.

| Stage | Deliverable | Plan groups | Work | Required evidence before activation | Rollback |
| --- | --- | --- | --- | --- | --- |
| R0 | Approval and protection | F00 | Review these eight reports; explicitly approve implementation scope. Re-read main/PR #18 divergence, user changes, current tests/model hashes and backup strategy. Create feature branch only after approval. | Read-only protection manifest and consistent old-data copy verified; no original checkpoint writes. | No feature enabled; no model/profile reset. |
| R1 | Foundation policy and storage | F01/F02/F03/F04/F05/F06/F07 | Add opt-in configuration, additive migrations, actors, exact approvals, tasks/events, redaction and audit receipts. Preserve existing owner/MFA and seven diagnostic tools. | Legacy schema writers and APIs still work; forged actor/cross-account/revocation/audit-failure tests pass. | Disable new routes and effects; retain additive records and original owners. |
| R2 | Bounded runtime and adapter contracts | F08/F09 | Introduce typed tool proposals, bounded loop and optional model-turn adapters; keep generate/stream and native tokenizer/checkpoint. | Unit + SQLite/runtime integration + actual native inference; malformed proposals fail closed; no extra external calls in local-only mode. | Disable runtime/tools; current text chat continues. |
| R3 | Isolation before executable tools | F28/F29/F18 after F17 | Implement rootless broker/egress boundaries, reviewed worker images, manifest validation and isolated plugin worker; host import never used. | Actual container tests show limits/no forbidden host mounts/network; missing backend explicitly unavailable; secret canaries absent. | Deny new execution; kill/drain workers and revoke activation. |
| R4 | Async gateway and recovery | F10/F11/F12 | Mount optional platform router, worker lifecycle and CLI; queue sessions with current HF serialization. | HTTP/SSE + core compatibility, busy behavior, lease fencing, crash/uncertain-effect recovery and cancellation tests. | Disable platform admission, drain workers; retain legacy API and data. |
| R5 | Scoped memory and skill packages | F14/F15/F16/F17/F19 | Add private FTS/documents/context first, bounded skills; select optional embeddings only after measured relevance/resource evidence. | Cross-account zero leakage, deletion/expiry, legacy notes/summaries compatibility and actual retrieval-to-answer workflow. | Use existing context/skills; retain protected documents; disable derived indexes. |
| R6 | Independent child tasks | F13 | Add child workspace identity, strict subset permissions, shared budgets and cancellation. Keep federation separate. | Real multi-step parent/child workflow; escalation denied; crash/cancel leaves no unauthorized orphan effects. | Disable spawn and drain children; keep parent/task receipts. |
| R7 | Durable schedules and Telegram pilot | F20/F21/F22/F23 | Read-only UTC jobs, standing authority rules, dedup/outbox, explicit pairing and first owned Telegram text workflow. | Signed/secret webhook checks, replay rejection, accepted-send timeout reconciliation and actual owned-account E2E. | Pause jobs/channels, revoke standing authority; reconcile unknown deliveries. |
| R8 | Additional messaging subsets | F24/F25 | Slack signed webhook/text and Discord verified interaction/text only; no claim of complete channel parity. | Provider-specific signature/replay tests plus actual owned-workspace/account E2E. | Disable individual channel, revoke connection and retain dedup/outbox. |
| R9 | Browser pilot; VM computer follow-up | F26 then optional F27 | Isolated Playwright + egress broker + action approvals first. Select/prove disposable VM backend separately before computer controls exist. | Actual controlled browser task and SSRF/credential fixtures; computer unavailable until VM input/display/cancellation/isolation tests pass. | Close ephemeral profiles/VM and revoke broker grants; no host desktop fallback. |
| R10 | Dashboard, measurement and release review | F30/F31/F32/F33/F34 | Add optional controls/attribution, metrics, optional extras, notices and paired benchmark reports; keep installer/logo/current UI. | Windows/Linux install + full existing regression + enabled-feature integration/security/E2E; rollback drill; actual comparison evidence. | Flags off after drain; old installation path and original data remain valid. |
| R11 | Optional OpenClaw bridge | F35 (not required) | Only if explicitly needed: narrowly authenticated read-only metadata/status bridge with exact protocol version and dependency availability. | Real version-negotiated scope-filtered bridge test; no full plugin/MCP compatibility claim. | Disable sidecar connection; native stack remains independent. |

The exact dependency graph in `../evidence/implementation-plan.json` is authoritative within this proposal. F18 executable plugins depend on F17 manifest approval, F28 isolation and F08 runtime mediation. Browser activation also requires the F29 egress policy. Gateway routing preserves current text inference while tools remain independently disabled. Dashboard elements show partial/unavailable capability honestly until its milestone passes.

## Per-change engineering protocol

Before each implementation group: recheck current main and protected hashes, confirm prerequisite contracts and Python compatibility, inspect the affected existing files/tests, select and license-review any optional dependencies, then implement one bounded change on the approved feature branch. Add tests at the exact destinations in [file plan](FILE_BY_FILE_IMPLEMENTATION_PLAN.md). Run focused tests followed by applicable existing regressions. Record failures and unsupported environments. Review API/schema/permission changes explicitly; no silent public contract break.

Before enabling a subsystem: exercise real SQLite/gateway/model/tool paths and relevant owned-backend E2E, not only mock contracts. Measure unchanged baseline and candidate on the frozen workload subset; security failures block exposure regardless of average success. Publish actual benchmark evidence and migrations/rollback steps in the PR. Code may be present but disabled while a backend/account is unavailable; that is not a completed capability.

Before release: confirm dependency/image/model license notices and a resolved SBOM; verify secret canaries, live grant revocation, emergency shutdown, approval digest checks and new account isolation; repeat protected file hashes; test current Windows/Linux local install and text chat without optional extras. Test rollback from a copy of migrated data. Keep original checkpoints and the existing training/promotion decision history immutable.

## Review and acceptance package

This review includes:

1. [OpenClaw source audit](OPENCLAW_REVERSE_ENGINEERING.md): pinned entry points, owners, contracts, state/persistence paths and source/runtime limits.
2. [Zenith architecture](ZENITH_CURRENT_ARCHITECTURE.md): main/workspace distinction, actual loaded model inventory, APIs/data/auth, deployment and baseline.
3. [Gap matrix](CAPABILITY_GAP_MATRIX.md): implemented, partial, missing and incompatible surfaces.
4. [Integration architecture](ZENITH_INTEGRATION_ARCHITECTURE.md): boundaries, protocols, data migration and rollback design.
5. [File plan](FILE_BY_FILE_IMPLEMENTATION_PLAN.md): exact source/config destinations, dependencies, expected behavior, tests, feature flags and rollback.
6. [Threat model](SECURITY_THREAT_MODEL.md): assets/actors, attack scenarios, mitigations and blocking tests.
7. [Benchmark plan](BENCHMARK_PLAN.md): measured baseline separated from proposed metrics/workloads.
8. This roadmap: dependency order, phase approval and incremental release gates.

Evidence accompanies the reports: hashed tracked-file source indexes, immutable source citation ledger, inventory/license/dependency summaries, actual cloned-main test log, local model inspection and native smoke results. These are source inventories and limited measurements, not full upstream runtime certification, a resolved transitive license opinion or performance promises. The package excludes live private profile contents, login/session/MFA data and repository/model binaries.

## Explicit remaining decisions and constraints

- Whether implementation should stop after the foundational runtime/gateway pilot or proceed through later owned-integration milestones is part of the approval scope. No execution is implied by this planning delivery.
- Rootless container/image/backend support must be verified on the intended deployment host; computer automation needs a selected isolated VM backend. Missing support disables the capability.
- Channel credentials/accounts and browser targets must be legitimately owned/authorized. External messages require action-specific consent and no credentials are requested for this audit.
- Embedding model, tracing exporter and optional bridge dependencies are not selected until evidence and license review justify them. No new model download is necessary for text-only compatibility.
- Existing PR #18 may change overlapping inference/reasoning files if later merged; reconcile that explicitly before implementation rather than silently overwriting it.
- No new training, knowledge distillation, frontier-model equivalence or performance gain is claimed. This is modular infrastructure around preserved Zenith.

No calendar completion promise is made. Isolation, channel E2E, Windows availability and recovery correctness determine effort; estimates must remain separate from measured results. No code push, PR modification, model promotion or deployment occurred for this audit. **Stopped at the requested audit/design boundary; implementation awaits review approval.**
