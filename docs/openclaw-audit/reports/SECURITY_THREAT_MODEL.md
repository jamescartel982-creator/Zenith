# Security threat model and release gates

**Audit date:** 2026-10-25 UTC. **OpenClaw:** `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. **Zenith main:** `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. This is an audit/design deliverable; no Zenith implementation changes are authorized in this delivery.

**Evidence labels:** S = source-verified at the pinned commit; M = measured here; D = upstream documentation/policy claim; P = proposed design; H = hypothesis requiring implementation or experiment. Source inspection does not establish successful live execution.

## Scope and assets

This is an architectural threat model, not a completed penetration test or certification. Existing Zenith auth/execution behavior is source-verified; proposed mitigations below are **P** until tested. No external exposure or security tools were enabled during this audit.

Protected assets: immutable model/checkpoint/tokenizer lineage; existing application data; account/project memories and task transcripts; provider/channel keys; owner/MFA secrets and session grants; sandbox/host boundary; authorization and effect receipts; dependency/artifact integrity; task compute budgets; external accounts and authorized targets. The host owner controls deployment and backup/key policy; the model never controls identity or administrative grants.

Actors: authenticated member, authenticated/elevated owner, anonymous internet client, unpaired channel sender, hostile document/web page, malicious skill/plugin/model output, compromised remote service, exhausted/buggy worker, host administrator and infrastructure attacker. Any external descriptions, content, manifests and outputs are untrusted until parsed and scoped. Even a correct model response is not an authorization decision.

## Trust boundaries

1. External client/channel → authenticated gateway actor.
2. Model/document/plugin text → typed **proposal**, not effect.
3. Typed proposal → live policy + exact-action approval + receipt.
4. Authorized effect → isolated worker/egress broker.
5. Actor/project → SQLite ACL and event replay.
6. Parent task → narrower child identity.
7. Gateway persistence → third-party accepted side effect.
8. Local metadata → optional observability export.

Existing owners: [agent/server.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/server.py#L1), [agent/admin.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/admin.py#L1), [agent/owner_mfa.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/owner_mfa.py#L1), [agent/execution.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/execution.py#L1). Account passwords are Argon2id; the current random admin-code verifier separately uses PBKDF2-HMAC-SHA256. Preserve these functioning semantics rather than claiming all current secrets already use one algorithm. Existing emergency stop must be checked by every new execution adapter.

## Threat register

| ID | Threat | Concrete trigger | Required design controls | Plan / tests | Release condition |
| --- | --- | --- | --- | --- | --- |
| T01 | Forged admin / confused deputy | Model, channel message or shared bearer claims owner authority | Server-created ActorContext, account ownership, live owner/MFA + permission checks; no model role mutation | F03/F04; tests/test_platform_permissions.py; tests/test_platform_security.py | Deny all forged identities with zero effects |
| T02 | Prompt injection in tool/skill/document | Untrusted text asks to leak secrets, skip approval or activate tools | Quote provenance, strict proposals and effect gate; text detector only defense in depth | F02/F08/F19; tests/test_platform_security.py | Injected instructions cannot grant/execute outside scope |
| T03 | Approval substitution / TOCTOU | Arguments, target, grant or emergency state change after user review | Canonical arg/target digest, one-use expiry, versioned actor/grant fence; recheck after await and before effect | F03/F04/F08; tests/test_platform_approvals.py | Mutation, expiry/revocation and shutdown deny; receipt records why |
| T04 | Cross-account memory or event leakage | Forged project ID, FTS join, replay cursor or task lookup crosses ownership | ACL predicate before content/ranking; membership checks on every query/replay; scoped dedup/deletion | F05/F06/F14; tests/test_platform_retrieval.py; tests/test_platform_events.py | Zero retrieved chunks/events/identifiers outside authorized scope |
| T05 | Plugin supply-chain / archive attack | Malicious manifest, symlink, traversal, dependency update or executable skill | Bounded manifest first, immutable artifact pin, review on change, safe extraction and isolated worker only | F17/F18/F19; tests/test_platform_plugins.py; tests/integration/test_platform_plugin_worker.py | No import in host; extraction cannot escape task workspace |
| T06 | Host filesystem / sandbox escape | Worker reads host secrets, mounts Docker socket, opens privileged namespace or abuses symlinks | No secret/home/socket mounts, rootless non-root isolated worker, readonly root, no caps, limits; VM for higher-risk code | F28/F29; tests/e2e/test_platform_sandbox.py | Known fixtures denied; no host fallback; acknowledge kernel residual risk |
| T07 | SSRF / network scope bypass | Redirect, rebinding, IPv6, subresource, CDP or metadata destination escapes policy | Broker controls resolution/connect and all browser egress; literal scoped labs separate; default private/link-local deny | F26/F29; tests/test_platform_egress.py; tests/e2e/test_platform_browser.py | Owned controlled redirect/DNS fixtures cannot reach forbidden listeners |
| T08 | Credential exposure | Provider key/MFA secret/cookie enters prompt, trace, exception or worker result | Secret references outside model context, metadata allowlist, redaction before egress, credential-free workers | F02/F07/F31; tests/test_platform_redaction.py | Synthetic secret canaries absent from responses/logs/export/worker context |
| T09 | Child privilege amplification | Subagent receives parent owner cookie/grant or expands target scope | Distinct child identity, strict subset capabilities, no implicit cookie/MFA reuse, combined budget limits | F13/F03; tests/test_platform_multi_agent.py | Broader child grant denied; parent cancellation stops new effects |
| T10 | Scheduler stale authority | Job continues after logout, grant expiry or emergency stop | Explicit standing service grant, fixed target/action/TTL/quota, lease fence and live auth revision | F20/F03; tests/test_platform_scheduler.py | Expired/revoked authority blocks job before effects |
| T11 | Channel spoof / replay | Fake webhook, bot token disclosure, reused timestamp or unpaired group sender | Provider signature/secret validation, bounded replay window, durable dedup and explicit sender/chat/thread pairing | F22–F25; tests/test_platform_channels.py; tests/e2e/test_platform_channels.py | Unpaired/forged/replayed envelope creates no authorized task/delivery |
| T12 | Duplicate external write / crash | Process dies after third party accepts send, before receipt commit | Transactional intent, idempotency keys where supported; unknown acceptance becomes reconciliation | F05/F21; tests/test_platform_recovery.py; tests/test_platform_outbox.py | No blind retry of uncertain non-idempotent effect |
| T13 | Resource exhaustion | Infinite tool loop, oversized schema/result, queue flood, plugin fork bomb | Admission quotas, bounded steps/tokens/wall time/results, per-account concurrency, worker memory/CPU/PID caps | F08/F10/F28; tests/test_platform_runtime.py; tests/e2e/test_platform_sandbox.py | Bounded rejection/termination and continued service for other accounts |
| T14 | Browser/desktop credential takeover | Tool imports host Chrome/keychain or operates real desktop | Disposable browser profile; VM-only computer transport; explicit write/click/upload approval | F26/F27; tests/e2e/test_platform_browser.py; tests/e2e/test_platform_computer.py | No host profile mounted; unavailable VM means capability denied |
| T15 | Audit tampering / missing receipt | DB edits, truncated tail, lost key, full disk or dropped writer queue | HMAC chain + protected key + external anchors; high-impact receipt synchronous/transactional before effect | F07; tests/test_platform_audit.py | Detect covered edits/truncation against anchors; full disk denies effect |
| T16 | UI/transport injection | Untrusted HTML/tool name opens scripts or cross-site state mutation | Escaped text, existing headers/cookie protection, origin/CSRF checks for approval/actions, no raw tool HTML | F10/F30; tests/test_platform_gateway.py; tests/test_platform_ui.py | Cross-origin approval and XSS fixtures fail with no state mutation |
| T17 | Legacy schema / data corruption | Partial migration, WAL copy or rollback overwrites newer user data | Transactional additive migrations; consistent SQLite backup; legacy-writer compatibility; restore reconciliation | F01/F00; tests/test_platform_migrations.py; tests/test_platform_compatibility.py | Crash leaves old data readable; old main writer still works |
| T18 | Remote model data exfiltration | Routing sends private documents or secrets to unapproved provider | Local-only flag enforced at transport boundary; per-project external consent, minimal context and account availability | F09/F16; tests/test_platform_model_turns.py; tests/test_platform_security.py | Local-only requests produce zero external transport calls |

## Defaults and human authority

All platform/tool/plugin/channel/browser/computer/scheduler flags start false. Owner status alone does not activate a restricted tool. The owner must authenticate, complete existing MFA, approve target scope and explicitly grant the capability. High-impact actions need a separate exact-action approval even when the tool capability is granted. Changes to target, arguments, package artifact, scope or privileged operation require a new review. Tools cannot call role/grant mutation endpoints using model-created values.

A global API bearer provides transport access, not owner identity. Do not copy OpenClaw's shared-secret full-operator behavior into Zenith. OpenClaw's explicit trusted-operator assumptions and default-off sandbox are deliberate source-level differences: [src/gateway/http-endpoint-helpers.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/gateway/http-endpoint-helpers.ts#L1), [src/agents/sandbox/config.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/agents/sandbox/config.ts#L1), [SECURITY.md:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/SECURITY.md#L1). These observations are not exploit findings against OpenClaw.

Browser pages, tool outputs and skills may contain adversarial instructions. Wrappers and scanners reduce accidental misuse but cannot establish trust. Source: [src/security/external-content.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/security/external-content.ts#L1). Enforce authorization and egress outside model inference. Existing local-only semantics must reject external provider calls even after fallback/retry.

## Residual risks and unavailable guarantees

Containers share a host kernel; a passed fixture suite does not prove universal sandbox-escape resistance. Stronger isolation may require disposable VMs and host hardening. A root attacker with the HMAC key can rewrite a local chain; external anchors improve detection only for anchored history. No exactly-once guarantee is possible for all third-party side effects. Cancellation cannot reverse an accepted external action; reconciliation and action-specific rollback are required. Model hallucinations remain possible; confidence is not permission or proof.

A compromised owner or provider may misuse legitimate authority. Least privilege, short grants, scoped keys, budget limits, provider terms and human review constrain exposure but do not eliminate trust. Windows rootless/container availability differs from Linux; no capability should fall back to unsandboxed host execution to appear functional. Discord/Slack/Telegram integrations and browser/computer backends remain unavailable until real owned-account/backend tests pass.

## External-access go/no-go checklist

Required before enabling new external routes: deny-by-default auth tests; cross-account isolation and event replay tests; grant revocation/emergency-stop race tests; exact approval and injection tests; real sandbox/egress fixtures for enabled execution; channel signature/replay tests for enabled integrations; receipt durability and crash recovery; secret-canary checks; security headers/origin/CSRF regression tests; dependencies/images pinned and reviewed; documented owner shutdown and rollback drill.

Unit tests alone do not satisfy these gates. Run hostile fixtures only in controlled owned environments without public target scanning. Record individual outcomes, environment/image/config hashes, failures and unavailable checks. Any critical authorization bypass, leaked secret, cross-account content or unintended effect blocks release regardless of average task accuracy. See [benchmark plan](BENCHMARK_PLAN.md) for measured denominators and [roadmap](IMPLEMENTATION_ROADMAP.md) for approval boundaries.
