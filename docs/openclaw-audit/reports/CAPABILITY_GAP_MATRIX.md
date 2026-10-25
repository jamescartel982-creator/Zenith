# Capability gap matrix

**Audit date:** 2026-10-25 UTC. **OpenClaw:** `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. **Zenith main:** `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. This is an audit/design deliverable; no Zenith implementation changes are authorized in this delivery.

**Evidence labels:** S = source-verified at the pinned commit; M = measured here; D = upstream documentation/policy claim; P = proposed design; H = hypothesis requiring implementation or experiment. Source inspection does not establish successful live execution.

Status describes **Zenith main 0.15.0**, not unmerged PR #18. “Implemented” is scoped to the named behavior, not parity with every upstream feature. OpenClaw support in this comparison is source-verified only. All additions in the final column are proposals, not installed capabilities.

| Capability | Zenith status | Current boundary | Proposed compatibility action | Plan IDs |
| --- | --- | --- | --- | --- |
| Native model and LoRA | Implemented | Agent/provider + immutable adapter lineage | Keep selected HF/PEFT engine; no OpenClaw model replacement | F00 |
| Local/remote model selection | Implemented / partial | Registry and federation already work for text | Extend optional structured turn contract; retain old generate/stream | F09 |
| HTTP/SSE gateway | Implemented / partial | FastAPI and SSE; no durable asynchronous task API | Add opt-in router and bounded inference worker | F10–F12 |
| OpenClaw WebSocket protocol | Incompatible | No versioned OpenClaw handshake in Zenith | Do not claim wire compatibility; optional narrow bridge only | F35 |
| Autonomous tool loop | Missing | Core builds context and generates text; fixed diagnostics invoked separately | Bounded typed calls, approval waits, results and cancellation | F08 |
| Tool authorization | Implemented / partial | Seven fixed capabilities; owner/MFA/scoped grants | Preserve gates; add per-tool/action permissions and approvals | F03–F07 |
| Task persistence/recovery | Partial | agent_tasks records fixed diagnostic plans | Versioned leases, fenced transitions, reconciliation | F05 |
| Multi-model federation | Implemented | Independent model drafts/reviews/synthesis | Keep existing orchestration owner; not multi-agent execution | F09 |
| Multi-agent runtime | Missing | No isolated child-task/workspace lifecycle | Budgeted children with strict subset delegation | F13 |
| Persistent account memory | Implemented | PersonalStore notes and summaries | Read existing data through ownership checks | F16 |
| Shared lexical knowledge | Implemented | Global FTS corpus; not private per-account ingestion | Retain shared corpus; new private documents use separate scoped tables | F14 |
| Semantic/project retrieval | Missing / partial | No vector engine or project-memory ACL | Scoped FTS first; optional measured embeddings later | F14–F16 |
| Skills | Partial | Validated prompt profiles/resources and protected selection | Manifest-first bounded text packages; no authority from skills | F19 |
| Executable plugins | Missing / incompatible | Trusted Python ProviderAdapter only; TS plugins cannot load | Isolated worker protocol; never import untrusted code into host | F17–F18 |
| Durable event service | Missing | Existing generation traces are not a durable event queue | Transactional sequenced task events and bounded subscribers | F06 |
| User scheduler | Missing | CI schedules are not per-user persistent jobs | UTC at/interval first; separate standing authority, cancellation | F20 |
| Messaging delivery | Missing | No paired Telegram/Slack/Discord inbound/outbound service | Authenticated identities, deduplication, approved outbox | F21–F25 |
| Browser automation | Missing | browser.py only opens Zenith UI locally | Isolated Playwright worker with controlled egress | F26 |
| Computer automation | Missing | No isolated desktop transport | Separate VM-only contract; unavailable until tested | F27 |
| General execution sandbox | Missing | App Docker image is not a tool sandbox | Rootless, deny-network broker; no host fallback | F28–F29 |
| Admin authentication | Implemented | Account Argon2id; admin code PBKDF2; owner TOTP | Preserve owner/MFA semantics and emergency stop | F03 |
| Role-based permissions | Partial | Owner/member distinctions and capability grants | Server-derived actor, roles, action scopes and revisions | F03 |
| High-impact approvals | Partial | Explicit capability grants, no generic action approval object | Bind approvals to canonical args/target/expiry/identity | F04 |
| Audit and redaction | Partial | Local bounded records; no crypto-chain guarantee | HMAC chain + external anchors, metadata redaction | F02/F07 |
| Tracing/performance | Partial | Local generation metrics; one model lock | Scoped task metrics; optional tracing exports disabled | F31 |
| Dashboard | Implemented / partial | Existing plain-JS chat/admin/memory UI | Add task/permission controls without changing logo or chat API | F30 |
| Installer/deployment | Implemented | Windows/Linux venv installer and non-root app image | Existing install flow remains default; optional extras only | F33 |
| Training/checkpoint governance | Implemented | CPT/SFT/DPO, parent verification, evaluations/rollback | No training changes; retain failed-gate status honestly | F00 |
| Multimodal execution | Partial / incompatible | Capability metadata does not make text transport multimodal | Separate compatible adapters later; no encoder/tokenizer substitution | Deferred |

## Evidence map

Gateway/runtime comparison: [src/gateway/server-start.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/gateway/server-start.ts#L1), [packages/agent-core/src/agent-loop.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/packages/agent-core/src/agent-loop.ts#L1) versus [agent/core.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/core.py#L1), [agent/server.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/server.py#L1), [agent/providers.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/providers.py#L1).

Models/federation: [agent/model_registry.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/model_registry.py#L1), [agent/orchestration.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/orchestration.py#L1), [agent/provider_adapters/openai_adapter.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/provider_adapters/openai_adapter.py#L1); OpenClaw plugin contract [src/plugins/types.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/plugins/types.ts#L1).

Memory/skills: [extensions/memory-core/src/memory/manager.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/extensions/memory-core/src/memory/manager.ts#L1), [src/skills/loading/workspace-skill-loader.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/skills/loading/workspace-skill-loader.ts#L1) versus [agent/storage.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/storage.py#L1), [agent/personal.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/personal.py#L1), [agent/summaries.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/summaries.py#L1), [agent/skills.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/skills.py#L1).

Execution/security: [src/agents/agent-tools.turn-authority.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/agents/agent-tools.turn-authority.ts#L1), [src/agents/sandbox/config.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/agents/sandbox/config.ts#L1), [src/security/external-content.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/security/external-content.ts#L1) versus [agent/execution.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/execution.py#L1), [agent/admin.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/admin.py#L1), [agent/owner_mfa.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/owner_mfa.py#L1), [agent/skill_access.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/skill_access.py#L1).

Channels/scheduler/browser/UI: [src/channels/plugins/types.plugin.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/channels/plugins/types.plugin.ts#L1), [src/cron/store.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/cron/store.ts#L1), [extensions/browser/src/browser-tool.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/extensions/browser/src/browser-tool.ts#L1), [src/agents/tools/computer-tool.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/src/agents/tools/computer-tool.ts#L1), [ui/src/main.ts:1](https://github.com/openclaw/openclaw/blob/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f/ui/src/main.ts#L1) versus [agent/browser.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/browser.py#L1), [agent/web/app.js:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/web/app.js#L1).

Training/deployment: [agent/continual.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/continual.py#L1), [agent/checkpoints.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/checkpoints.py#L1), [agent/deployment.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/deployment.py#L1), [install.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/install.py#L1), [Dockerfile:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/Dockerfile#L1).

## Deliberate incompatibilities and non-goals

OpenClaw TypeScript plugins, native macOS/Windows applications and its WebSocket wire protocol are not Python packages. Wholesale vendoring would introduce an unsupported Node stack and a different security/data model. A later explicitly configured bridge may expose a small compatible surface, but cannot claim full plugin or protocol parity. OpenClaw's trusted-operator shared-secret semantics and sandbox-off default must not weaken Zenith's account isolation or default-deny execution.

No model weights, private vendor model activations, proprietary families or new training results are supplied by this integration. Existing model licenses, tokenizer identity and checkpoint gates remain in force. Browser, desktop, channel and sandbox features stay unavailable until their actual integration/security tests pass. The current two inference probes establish load/route compatibility only.

See [file plan](FILE_BY_FILE_IMPLEMENTATION_PLAN.md) for exact destinations and [threat model](SECURITY_THREAT_MODEL.md) for release gates.
