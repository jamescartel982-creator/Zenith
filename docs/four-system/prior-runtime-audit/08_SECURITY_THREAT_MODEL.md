# Security and trust model

**2026-10-26 — audit/proposal only.** No new bridge, model endpoint, service, profile, credential or deployment has been enabled; existing native code/configuration/state remains unchanged.

Protect immutable model/tokenizer/adapter/checkpoints, native histories/memories/skills, identities/MFA, service/platform credentials, authorized targets, native task ownership, audit and backups. Trust boundaries are user→bridge, bridge→native agent API, native model provider→Zenith inference, native agent→tool/environment/network, profile→state and operator→service manager/update. Models, messages, web/doc content, plugins/skills/MCP descriptions and results are untrusted data. Task authentication does not authorize every native internal tool.

| Threat | Required additive control and preserved boundary | Acceptance |
| --- | --- | --- |
| Forged administrator/model self-grant | Server-derived actors, current capability/target/expiry/effect and actual human approval; no admin secret in prompts | Forged roles, stale MFA/grants, changed arguments and cross-tenant IDs deny before dispatch |
| Owner token disguised as per-user scope | Paired/scoped OpenClaw WS plus native tool policy; Hermes profile credentials/routes/capabilities; isolated tenant runtimes | Narrow x-openclaw-scopes cannot reduce shared-secret HTTP owner authority; cross-profile requests denied |
| Prompt injection/package execution | Independent permissions, deliberate native skill/plugin/MCP installation and isolated execution | Untrusted content cannot change route/credentials/grants; discovery is not installation approval |
| Native terminal reads host/other-runtime secrets | No host root/home or Docker socket mounts; supported native environment/secret controls and separate identities | Actual selected native shell cannot read excluded data; unsupported enforcement remains BLOCKED |
| Unauthorized shell/network/remote effects | Owned sandbox/VM/container, native approvals, explicit target, egress and CPU/RAM/PID/output/time/concurrency limits | Real process/file/network/cancellation probes for each native backend; Zenith sandbox tests do not automatically cover Hermes/OpenClaw |
| SSRF/provider or callback injection | Allowed service origins, private authenticated transport, DNS/redirect/metadata/private-target restrictions | Rebinding, redirect, URL/key/provider override and target-scope denial tests |
| Memory/session leaks | Tenant+runtime+profile+conversation mapping; native scoped reads; no private SQL or automatic content merge | Two-profile/account history/search/summary/reset/delete/restart isolation |
| Duplicate writes/delivery/jobs | One backend/delivery owner and correct native session/profile/credential/submission domain | Lost ack, rotation, reset and uncertain retry cannot duplicate an effect elsewhere |
| False completion/cancellation | Preserve native ack, terminal, partial/incomplete/error and cancel/status semantics | HTTP200/first SSE chunk is not completion; unknown external outcomes require reconciliation |
| Secret/log leakage | Private native stores, secret handles at transport boundary, minimal redacted bridge metadata and explicit exports | Canary keys absent from model prompts/events/logs/exports; pattern redaction is not a universal secret detector |
| Runaway or restarted work | Bounded calls/resources and owned service/process-group cancellation; native restart semantics | Kill/restart/expiry/emergency tests; never blindly replay accepted external work |
| Supply chain/update drift | Exact source/lock/artifact hashes, attribution, candidate copies and explicit promotion | No live pin mutation, unsupported dependency merge or patch; new versions require baseline review |
| Audit/backup tampering | Durable receipts, private keys, external integrity anchors where applicable and consistent native backups | Alter/drop/IO-failure/recovery tests; root/key-owner compromise is outside local HMAC assurance |

Original native UIs/CLIs and original profiles keep their native trust model. Do not claim the bridge retroactively secures every direct native entry point. For untrusted tenants, use separate isolated runtime/profile boundaries, not one shared personal-owner key plus a user header. Supported native tool policies and OS isolation must actually enforce the intended boundary. If they cannot, keep the bridge capability disabled and request approval for the exact source change; do not silently remove tools, bypass approvals or patch native policies.

High-impact sends/writes, security diagnostics, remote execution, credential operations, publishing and destructive actions require appropriate explicit authority and real native approvals. Security diagnostics also need defined authorized targets and safe limits. No unauthorized intrusion, credential theft, malware deployment or retaliation is proposed.

Emergency stop stops new bridge admissions, revokes its grants and cancels/stops only newly owned work/services. It does not commandeer original user processes or undo an already completed external action. Native background/cloud jobs require their own pause/cancel/stop and reconciliation. External access remains blocked until real auth/TLS/origin/CSRF/rate/quota/tenant/tool/restart tests pass. Containers share a kernel; finite tests do not establish universal injection/escape resistance.
