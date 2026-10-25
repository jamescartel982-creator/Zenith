# File-by-file implementation plan

**Audit date:** 2026-10-25 UTC. **OpenClaw:** `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. **Zenith main:** `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. This is an audit/design deliverable; no Zenith implementation changes are authorized in this delivery.

**Evidence labels:** S = source-verified at the pinned commit; M = measured here; D = upstream documentation/policy claim; P = proposed design; H = hypothesis requiring implementation or experiment. Source inspection does not establish successful live execution.

**All entries are proposals (P). No destination below has been created or edited in Zenith.** Plan IDs group related changes but each row identifies one exact destination. New test destinations are proposed too, not existing passing tests. Existing test names in the table must be confirmed/reused during implementation; any absent name is a planned focused test file. Shared test files validate interactions rather than duplicating each implementation function.

## Dependency and rollout rules

Group dependencies are mandatory before a dependent feature is enabled. A reviewed implementation may split small PRs further, but must not bypass live authorization, receipt persistence or isolation. F00 starts only after the user approves implementation. F35 is optional/deferred; F27 is unavailable until a real VM backend is selected and tested. The proposed module names do not imply current capability.

| Group | Capability | Requires | Rollback / failure behavior |
| --- | --- | --- | --- |
| F00 | Preservation and baseline | approval | No feature enabled; no changes to weights or saved profile. |
| F01 | Configuration and additive schema | F00 | Disable platform_enabled; leave new tables intact and old schema unchanged. |
| F02 | Redaction | F01 | Disable platform routes/export; retain redaction on stored evidence. |
| F03 | Permissions | F01, F02 | Revoke platform grants and disable new tools; retain current owner/MFA paths. |
| F04 | Action approvals | F03 | Deny pending approvals; never execute stale approved actions on rollback. |
| F05 | Durable tasks | F01, F03 | Stop admission; cancel/drain and fence outstanding leases; retain task receipts. |
| F06 | Durable events | F05 | Stop subscribers; preserve terminal/approval events and replay cursors. |
| F07 | Audit chain | F02, F04, F06 | Stop new effects on audit failure; retain chain, key and external anchor references. |
| F08 | Tool runtime | F04, F05, F06, F07 | Set platform_runtime_enabled=false; cancel/drain; old text path continues. |
| F09 | Structured model turns | F08 | Set platform_tools_enabled=false; restore existing text-only adapter behavior. |
| F10 | Async gateway | F08, F09 | Disable platform routes; retain legacy chat/admin routes and stored data. |
| F11 | Application lifecycle | F10 | Stop platform workers before closing DB; legacy app remains usable. |
| F12 | CLI integration | F11 | Disable opt-in commands; retain existing installer/run/chat commands. |
| F13 | Multi-agent | F08, F10 | Disable child creation, cancel/drain children; preserve parent receipts. |
| F14 | Scoped lexical retrieval | F01, F03 | Disable private ingestion/search; retain encrypted-at-rest storage policy and ACLs. |
| F15 | Optional semantic retrieval | F14 | Disable embeddings; use scoped lexical fallback; keep source documents intact. |
| F16 | Memory context | F14, F09 | Disable new context assembly; existing PersonalStore/summaries remain unchanged. |
| F17 | Plugin manifests | F03, F07 | Disable registry activation; retain approved artifact provenance. |
| F18 | Plugin workers | F17, F28, F08 | Stop workers; revoke activation; never fall back to in-host import. |
| F19 | Skill packages | F17, F16 | Disable package layer; retain existing built-in validated skills. |
| F20 | Scheduler | F05, F06, F04 | Pause all jobs; fence leases and revoke standing grants; do not rerun missed writes. |
| F21 | Outbox | F05, F04, F07 | Pause deliveries; mark uncertain sends for reconciliation; do not blindly retry. |
| F22 | Channel interface | F10, F21 | Disable channel ingress, revoke pairings/worker credentials; retain receipts. |
| F23 | Telegram subset | F22 | Disable Telegram ingress/outbox and revoke bot connection; retain dedup state. |
| F24 | Slack subset | F22 | Disable Slack ingress/outbox and revoke connection; retain replay receipts. |
| F25 | Discord subset | F22 | Disable Discord ingress/outbox and revoke connection; retain replay receipts. |
| F26 | Browser worker | F28, F29, F04, F10 | Close isolated contexts; disable browser tools and egress; remove derived temporary profiles. |
| F27 | Computer VM | F26 | Power down disposable VM and revoke transport; never redirect to real host desktop. |
| F28 | Sandbox broker | F03, F04, F07 | Deny new execution; cancel/kill workers; no unsandboxed fallback. |
| F29 | Sandbox policy | F28 | Revoke image/egress approvals; drain workers; keep text-only operation. |
| F30 | Dashboard | F10, F16, F20, F22 | Hide platform panels; retain current chat/logo and API compatibility. |
| F31 | Metrics and tracing | F06, F02 | Disable exports/instrumentation; retain current local metrics behavior. |
| F32 | Acceptance harness | F10, F13, F15, F18, F23, F24, F25, F26, F31 | Disable release gate only by explicit reviewed policy; keep baseline evidence immutable. |
| F33 | Optional packaging | F01 | Use existing base install; uninstall optional extras only after workers drain. |
| F34 | Documentation and notices | F32, F33 | Preserve release evidence and attribution; revert code only with compatible documented flags. |
| F35 | Optional read-only bridge | F10, F03 | Disable bridge; revoke sidecar credentials; native operation remains independent. |

## Exact source/configuration destinations

Each flag below defaults off. Feature activation also checks `platform_enabled` and all dependent security/backend flags. Per-tool owner grants remain separately disabled until explicitly activated, including for the owner. Flags are operator configuration, not model-writeable state.

| Change ID | Exact destination | Change | Expected behavior | Verification destinations | Activation |
| --- | --- | --- | --- | --- | --- |
| F00.1 | `scripts/platform_protection.py` | new | Read-only capture of commit, approved file hashes and model lineage; no private profile dump. Compare before/after; never mutate checkpoint. | `tests/test_platform_protection.py` | none |
| F01.1 | `agent/platform_config.py` | new | Validated opt-in flags, quotas and dependency availability; fail closed for unavailable worker backends. | `tests/test_platform_config.py` | all default false |
| F01.2 | `agent/config.py` | modify | Append backwards-compatible platform settings only; preserve existing Settings positional/default behavior and current provider selection. | `tests/test_platform_config.py`, `tests/test_config.py` | platform_enabled |
| F01.3 | `.env.example` | modify | Commented examples without secrets, default-off flags and local-only admission. | `tests/test_platform_config.py` | platform_enabled |
| F01.4 | `agent/platform_migrations.py` | new | Own platform_schema_migrations and additive platform_* tables through existing SQLite connection; versioned atomic migrations, no legacy column changes. | `tests/test_platform_migrations.py` | platform_enabled |
| F01.5 | `agent/platform_repository.py` | new | Bounded transactional queries, ACL join helpers, consistent SQLite backup/restore preflight; never open duplicate memory DB. | `tests/test_platform_migrations.py`, `tests/test_platform_repository.py` | platform_enabled |
| F02.1 | `agent/redaction.py` | new | Redact known token/credential forms before model/log/tool egress; output quotas and sensitive-field allowlist. | `tests/test_platform_redaction.py` | platform_enabled |
| F03.1 | `agent/permissions.py` | new | Server-derived ActorContext; per-tool role/target policies, revisions and strict subset delegation; no model-created permissions. | `tests/test_platform_permissions.py`, `tests/test_platform_security.py` | platform_tools_enabled |
| F03.2 | `agent/execution.py` | modify | Add adapter hook to live grant/MFA/emergency checks for platform effects; preserve seven legacy fixed capabilities and APIs. | `tests/test_execution.py`, `tests/test_platform_security.py` | platform_tools_enabled |
| F04.1 | `agent/approvals.py` | new | One-use action approvals bind actor, target, tool version, canonical argument digest and expiry; mutate-after-approval denied. | `tests/test_platform_approvals.py`, `tests/test_platform_security.py` | platform_tools_enabled |
| F05.1 | `agent/task_store.py` | new | Scoped task/checkpoint/lease records, compare-and-swap transitions, durable tool receipts and unknown-effect reconciliation. | `tests/test_platform_tasks.py`, `tests/test_platform_recovery.py` | platform_runtime_enabled |
| F06.1 | `agent/event_bus.py` | new | Transactional sequenced scoped events with bounded live queues/replay; backpressure cannot lose terminal/approval records. | `tests/test_platform_events.py`, `tests/test_platform_recovery.py` | platform_runtime_enabled |
| F07.1 | `agent/audit_chain.py` | new | Metadata HMAC chain, protected external key references and periodic external anchors; deny high-impact effects if receipt persistence fails. | `tests/test_platform_audit.py`, `tests/test_platform_security.py` | platform_tools_enabled |
| F08.1 | `agent/tool_protocol.py` | new | Strict typed tool proposals/results, bounded JSON Schema subset, versioning/effect class/usage/error types; reject unknown fields and names. | `tests/test_platform_tool_protocol.py` | platform_tools_enabled |
| F08.2 | `agent/tool_registry.py` | new | Resolve approved exact tool versions/dependencies; availability separate from authorization; validate args before policy and execution. | `tests/test_platform_tool_registry.py`, `tests/test_platform_security.py` | platform_tools_enabled |
| F08.3 | `agent/runtime.py` | new | Bounded plan-act-observe loop, approval waits, per-effect rechecks, quota/deadline/cancel propagation and durable transitions. | `tests/test_platform_runtime.py`, `tests/test_platform_recovery.py`, `tests/integration/test_platform_runtime.py` | platform_runtime_enabled |
| F09.1 | `agent/model_capabilities.py` | modify | Add optional structured-turn capability/protocol without changing existing ProviderAdapter implementers; unknown support remains unknown. | `tests/test_platform_model_turns.py` | platform_tools_enabled |
| F09.2 | `agent/providers.py` | modify | Optional generate_turn adapter around current factories; serialize existing HF model; no replacement tokenizer/loading behavior. | `tests/test_platform_model_turns.py`, `tests/integration/test_platform_native.py` | platform_tools_enabled |
| F09.3 | `agent/provider_adapters/openai_adapter.py` | modify | Explicit tool-turn request/result conversion with schema and account capability validation; retain old text rejection path. | `tests/test_platform_model_turns.py`, `tests/integration/test_platform_providers.py` | platform_tools_enabled |
| F09.4 | `agent/provider_adapters/anthropic_adapter.py` | modify | Explicit content/tool-use block conversion and bounded usage/cancellation; retain old text contract. | `tests/test_platform_model_turns.py`, `tests/integration/test_platform_providers.py` | platform_tools_enabled |
| F09.5 | `agent/provider_adapters/local_adapter.py` | modify | Negotiate local tool protocol; unsupported HF/Ollama endpoints remain text-only; strict native JSON proposal experiment separately gated. | `tests/test_platform_model_turns.py`, `tests/integration/test_platform_native.py` | platform_tools_enabled; native_json_tools_enabled |
| F10.1 | `agent/gateway.py` | new | Optional authenticated /api/platform tasks/events/approval/memory routes; bounded async admission, explicit unavailable/busy errors. | `tests/test_platform_gateway.py`, `tests/integration/test_platform_gateway.py` | platform_enabled |
| F11.1 | `agent/server.py` | modify | Mount new router with existing auth dependencies and startup/drain hooks; keep all legacy endpoints/cookies/schema. | `tests/test_server.py`, `tests/test_platform_gateway.py`, `tests/integration/test_platform_gateway.py` | platform_enabled |
| F11.2 | `agent/core.py` | modify | Opt-in runtime submission/context adapter only; default text generation and lock/save lifecycle remain unchanged. | `tests/test_platform_compatibility.py`, `tests/integration/test_platform_native.py` | platform_runtime_enabled |
| F12.1 | `agent/commands.py` | modify | Explicit opt-in task inspect/cancel and registry status commands; no implicit tool activation from chat commands. | `tests/test_platform_commands.py` | platform_enabled |
| F13.1 | `agent/multi_agent.py` | new | Child identity/workspace lifecycle with strict subset delegated capability scopes, step/token budgets and parent cancellation. | `tests/test_platform_multi_agent.py`, `tests/integration/test_platform_multi_agent.py` | platform_multi_agent_enabled |
| F14.1 | `agent/retrieval.py` | new | Private account/project documents and FTS in additive tables; ACL before rank/content, provenance, expiration/dedup/deletion. | `tests/test_platform_retrieval.py`, `tests/test_platform_security.py`, `tests/integration/test_platform_memory.py` | platform_memory_enabled |
| F15.1 | `agent/semantic_memory.py` | new | Optional revision-pinned embeddings with licensed model and derived index version; lexical fallback and complete deletion. | `tests/test_platform_semantic_memory.py`, `tests/integration/test_platform_memory.py` | platform_embeddings_enabled |
| F16.1 | `agent/context_manager.py` | new | Bounded quoted context from existing PersonalStore/summaries plus scoped retrieval; no duplicate database or summary authority. | `tests/test_platform_context.py`, `tests/integration/test_platform_native.py` | platform_memory_enabled |
| F17.1 | `agent/plugins/__init__.py` | new | Package marker only; no eager imports or plugin execution. | `tests/test_platform_plugins.py` | platform_plugins_enabled |
| F17.2 | `agent/plugins/manifest.py` | new | Bounded declarative manifests, artifact SHA pinning, path/archive validation, requested-capability display and reapproval on change. | `tests/test_platform_plugins.py`, `tests/test_platform_security.py` | platform_plugins_enabled |
| F17.3 | `agent/plugins/registry.py` | new | Metadata-only discovery/approval/availability records; signatures are provenance only; no in-host untrusted import. | `tests/test_platform_plugins.py`, `tests/test_platform_security.py` | platform_plugins_enabled |
| F18.1 | `agent/plugins/worker.py` | new | Sandbox worker framed JSON discovery/invoke protocol; capability mediation, output/CPU quotas, cancellation and crash cleanup. | `tests/test_platform_plugin_worker.py`, `tests/integration/test_platform_plugin_worker.py` | platform_plugins_enabled |
| F19.1 | `agent/skill_packages.py` | new | Hash-pinned bounded skill text/resources, source attribution and injection labels; installation never grants execution authority. | `tests/test_platform_skill_packages.py`, `tests/test_platform_security.py` | platform_skill_packages_enabled |
| F19.2 | `agent/skills.py` | modify | Optional approved package resource adapter; preserve built-in profiles and commands; never load executable skill code. | `tests/test_platform_skill_packages.py` | platform_skill_packages_enabled |
| F19.3 | `agent/skill_access.py` | modify | Apply existing protected profile access to optional skills; tool permissions remain separately enforced. | `tests/test_platform_skill_packages.py`, `tests/test_platform_security.py` | platform_skill_packages_enabled |
| F20.1 | `agent/scheduler.py` | new | Persist UTC at/interval jobs, lease claims, overlap/misfire policies; read-only initial jobs with distinct standing authority. | `tests/test_platform_scheduler.py`, `tests/test_platform_recovery.py`, `tests/integration/test_platform_scheduler.py` | platform_scheduler_enabled |
| F21.1 | `agent/outbox.py` | new | Atomic intent/receipt records, bounded retries, idempotency where supported; uncertain accepted writes need reconciliation. | `tests/test_platform_outbox.py`, `tests/test_platform_recovery.py` | platform_channels_enabled |
| F22.1 | `agent/channels/__init__.py` | new | Package marker; no import-time credential reads or network connections. | `tests/test_platform_channels.py` | platform_channels_enabled |
| F22.2 | `agent/channels/base.py` | new | Authenticated ingress/dedup and explicit sender/chat/thread-to-account pairing; per-channel output approval. | `tests/test_platform_channels.py`, `tests/test_platform_security.py` | platform_channels_enabled |
| F23.1 | `agent/channels/telegram.py` | new | Minimal owned-bot webhook inbound/text outbound; verify configured webhook secret and pairing; unconfigured means unavailable. | `tests/test_platform_telegram.py`, `tests/e2e/test_platform_channels.py` | platform_telegram_enabled |
| F24.1 | `agent/channels/slack.py` | new | Minimal signed timestamp-bounded Slack ingress and approved text send; replay protection and explicit account scopes. | `tests/test_platform_slack.py`, `tests/e2e/test_platform_channels.py` | platform_slack_enabled |
| F25.1 | `agent/channels/discord.py` | new | Minimal verified interaction webhook and approved text reply; Ed25519 validation and pairing; no voice claims. | `tests/test_platform_discord.py`, `tests/e2e/test_platform_channels.py` | platform_discord_enabled |
| F26.1 | `agent/browser_automation.py` | new | Isolated Playwright worker/profile; policy-checked egress and action approval; no host browser cookies/profile import. | `tests/test_platform_browser.py`, `tests/e2e/test_platform_browser.py`, `tests/test_platform_security.py` | platform_browser_enabled |
| F27.1 | `agent/computer_automation.py` | new | VM desktop transport with input/display limits and explicit approval; unsupported until compatible backend E2E passes. | `tests/test_platform_computer.py`, `tests/e2e/test_platform_computer.py` | platform_computer_enabled |
| F28.1 | `agent/sandbox.py` | new | Broker contract, image allowlist, isolated filesystem paths and resource/network requirements; missing backend denies code execution. | `tests/test_platform_sandbox.py`, `tests/test_platform_security.py` | platform_sandbox_enabled |
| F28.2 | `agent/sandbox_docker.py` | new | Rootless container lifecycle, no socket mount into workers, readonly root/nonroot/cap-drop/seccomp/quotas, kill/drain cleanup. | `tests/test_platform_sandbox.py`, `tests/e2e/test_platform_sandbox.py` | platform_sandbox_enabled |
| F29.1 | `config/sandbox-policy.example.json` | new | Document approved immutable image digests, no-network default and explicit quotas; no embedded secrets/host mounts. | `tests/test_platform_sandbox.py` | platform_sandbox_enabled |
| F29.2 | `agent/egress_policy.py` | new | Broker-owned DNS/redirect/subresource and IPv4/IPv6 target enforcement; block metadata/private/loopback by default. | `tests/test_platform_egress.py`, `tests/e2e/test_platform_browser.py` | platform_browser_enabled |
| F30.1 | `agent/web/platform.js` | new | Optional task/approval/memory/job/connection panels; explicit availability and model attribution; escape untrusted text. | `tests/test_platform_ui.py`, `tests/e2e/test_platform_workflows.py` | platform_enabled |
| F30.2 | `agent/web/index.html` | modify | Preserve logo and chat markup; mount optional platform panel only when enabled. | `tests/test_platform_ui.py`, `tests/e2e/test_platform_workflows.py` | platform_enabled |
| F30.3 | `agent/web/app.js` | modify | Load optional panel adapter without changing existing login/chat/SSE flow; no credentials in model prompts. | `tests/test_platform_ui.py`, `tests/e2e/test_platform_workflows.py` | platform_enabled |
| F30.4 | `agent/web/style.css` | modify | Add scoped panel styles; preserve current layout/branding and mobile chat behavior. | `tests/test_platform_ui.py`, `tests/e2e/test_platform_workflows.py` | platform_enabled |
| F31.1 | `agent/telemetry.py` | new | Task/span metrics and optional redacted OpenTelemetry export; unknown tokens/cost remain unknown. | `tests/test_platform_telemetry.py`, `tests/test_platform_redaction.py` | platform_telemetry_enabled; exports disabled |
| F31.2 | `agent/monitoring.py` | modify | Adapter for platform metadata into current bounded per-account monitoring; no unbounded raw prompt traces. | `tests/test_platform_telemetry.py`, `tests/test_platform_security.py` | platform_telemetry_enabled |
| F32.1 | `scripts/platform_benchmark.py` | new | Paired baseline/candidate workload runner; fixture/config hashes, timings, outcomes and honest unavailable results. | `tests/test_platform_benchmark.py`, `tests/e2e/test_platform_workflows.py` | manual evaluation only |
| F32.2 | `agent/evaluation/platform-v1.json` | new | Frozen licensed deterministic workload definitions, slices, scoring and owned-lab scope; no training reuse. | `tests/test_platform_benchmark.py` | manual evaluation only |
| F32.3 | `.github/workflows/platform.yml` | new | Windows/Linux compatibility plus Linux container/security gates; real integration jobs explicitly gated by dependencies/credentials. | `tests/test_platform_benchmark.py`, `tests/e2e/test_platform_sandbox.py` | opt-in CI workflow |
| F33.1 | `pyproject.toml` | modify | Optional extras for platform/browser/sandbox/telemetry; keep base Python/CPU installation and existing extras. Pin after dependency/license review. | `tests/test_platform_installation.py` | optional extras only |
| F33.2 | `install.py` | modify | Optional named extras installation and availability diagnostics; existing --mode local and virtualenv path remain unchanged. | `tests/test_platform_installation.py` | optional installer argument |
| F34.1 | `THIRD_PARTY_NOTICES.md` | new | Per-adaptation OpenClaw commit/path/hash and MIT/scoped notices; selected Python package/model licenses, no asset relicensing. | `tests/test_platform_release.py` | release metadata only |
| F34.2 | `docs/platform/architecture.md` | new | Implemented boundaries, flags, data migration and API contracts; unavailable items explicitly listed. | `tests/test_platform_release.py` | release metadata only |
| F34.3 | `docs/platform/operations.md` | new | Credential/MFA management, backups, key anchors, drain/revoke/rollback and Windows/Linux optional backend instructions. | `tests/test_platform_release.py` | release metadata only |
| F34.4 | `docs/platform/benchmark-results.md` | new | Actual measured paired results and source/config hashes; retain baseline and failures, never estimates as results. | `tests/test_platform_release.py` | release metadata only |
| F35.1 | `agent/openclaw_bridge.py` | new | Deferred narrow read-only status/metadata bridge with pinned negotiated protocol, scope filtering and explicit credentials; not full compatibility. | `tests/test_platform_openclaw_bridge.py`, `tests/integration/test_platform_openclaw_bridge.py` | platform_openclaw_bridge_enabled |

## New package and test-file responsibilities

The table lists each proposed source/config path once. `agent/plugins/__init__.py` and `agent/channels/__init__.py` must remain inert. No changes are proposed to trained checkpoints, tokenizer, adapters, existing dataset bundles, base inference algorithms, active saved profile, or current training/deployment owners. New API routes share the current server authentication dependencies rather than constructing a second admin system.

`tests/test_platform_security.py` is the shared regression boundary for forged actors, account crossover, prompt injection, approval-argument mutation, expired/revoked grants, emergency stop and child privilege amplification. `tests/test_platform_recovery.py` injects process death and delayed accepted effects, verifies lease fencing and uncertain-write reconciliation. `tests/test_platform_compatibility.py` checks current HTTP/stream/CLI responses and old SQLite writer compatibility. Focused unit test modules in the table validate the relevant contract; integration modules compose real SQLite/gateway/runtime/provider boundaries. The E2E modules require actual isolated backends or owned channel credentials and report unavailable instead of silently passing. `tests/test_platform_installation.py` covers Windows/Linux base venv/CLI installation with optional extras absent. `tests/test_platform_release.py` checks flags, provenance, notices, compatibility docs and unchanged protection manifests.

## Dependency choices and release review

| Area | Proposed dependency decision | Required pre-merge evidence |
| --- | --- | --- |
| Gateway/store/config | Existing FastAPI/Pydantic/Uvicorn + stdlib asyncio/sqlite3 | Match current Python 3.10/3.12 matrix; transaction/timeout/close tests |
| HTTP channel/worker clients | Optional HTTPX runtime extra; no global dependency assumption from dev tests | Pin compatible version, resolve dependencies, collect license and transport bounds tests |
| Tool schemas | Strict Pydantic/explicit bounded JSON Schema subset first | Document supported schema dialect/constraints; reject unsupported schemas rather than claim full MCP compliance |
| Code/plugin isolation | Rootless Docker backend through optional broker/client | Pin image digests, Docker/API version matrix, Linux and Windows availability checks, image SBOM/notices |
| Browser | Optional Python Playwright and pinned browser image | Package/browser licenses and runtime notices, actual egress-isolated E2E |
| Discord signatures | Existing compatible cryptography where available; select extra only if required | Ed25519 timestamp/replay fixtures and license resolution |
| Scheduler | stdlib UTC one-shot/interval first | No hidden cron semantics; full cron/tzdata deferred until dependency/DST review |
| Semantic retrieval | FTS first, embedding model/library not yet selected | Licensed pinned model, measured retrieval lift, deletion/ACL/CPU footprint tests |
| Metrics | Optional OpenTelemetry extra | License/version resolution and proof no unintended network/secret exports |
| OpenClaw | No runtime/npm dependency in base Zenith | If source adapted, MIT + scoped notices, exact path/hash/commit; optional bridge version negotiation only |

A resolved transitive SBOM and image/model artifact license review are required before release, not invented from upstream `package.json` fields. Do not add npm/Node to the default Python installation. Native OpenClaw plugins cannot be installed as Python packages. No third-party provider model or output is used for training in this plan.

## Migration and rollback contract

Before implementation capture current main, resolve the still-open PR #18 boundary, compare user workspace divergence, and take an authorized consistent backup without modifying production weights. New schema migrations create only additive `platform_*` objects and a migration ledger. Tests must show current main can still write legacy tables after migration. Additive rollback disables feature access and preserves data; it does not drop tables or overwrite user databases. Audit receipts and external anchors survive rollback. Any full restore needs a separate explicit data-loss/reconciliation decision.

Before enabling each group: baseline regression, focused unit tests, relevant integration/security tests, backend availability and real-path E2E where applicable. If credentials/VM/container support are absent, the corresponding capability stays unavailable; a fake provider contract test is not an E2E success. Never run untrusted plugin imports or host shell as an availability fallback.

See [architecture](ZENITH_INTEGRATION_ARCHITECTURE.md), [threat model](SECURITY_THREAT_MODEL.md), [benchmarks](BENCHMARK_PLAN.md) and [roadmap](IMPLEMENTATION_ROADMAP.md). Machine-readable counterpart: `../evidence/implementation-plan.json`.
