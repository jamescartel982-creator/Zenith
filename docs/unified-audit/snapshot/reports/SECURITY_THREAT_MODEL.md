# Security threat model

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Assets, actors and boundaries

Protect immutable model/adapter/tokenizer artifacts; user conversations and memory; credentials; host and remote systems; task grants; backups and audit integrity. Actors are authenticated users, owners, delegated workers, untrusted model outputs, websites, documents, remote tools, plugins, messaging peers and compromised service accounts. Boundaries are client→gateway, gateway→policy/store, model→tool proposal, policy→worker, worker→network/host, package→loader and tenant→memory. Compromised host/root is outside a process sandbox's protection; do not describe the HMAC log or Docker as proof against it.

Existing account Argon2id, owner MFA/session checks, revision-scoped grants and emergency stop remain authoritative. A gateway bearer establishes transport access, not owner privileges. The original random owner-code hashing and account password hashing serve different existing paths; do not replace either with a prompt secret. Never place credentials or MFA seeds in model context.

| Threat | Required control / destination | Acceptance / residual limit |
| --- | --- | --- |
| Forged owner or model self-authorization | agent/permissions.py and approvals.py derive actors from current server-side sessions, MFA and revision; object-level account/project ownership | Forged JSON role, expired session, revoked grant, cross-account task and argument mutation deny before any side effect; LLM cannot mint grants |
| Prompt injection from web/skill/MCP output | tool_protocol.py labels untrusted content; policy computes permissions independently; approvals bind normalized arguments, target scope and revision | Injected instructions never enlarge scope; formatting/redaction is not the security boundary |
| Code execution and escape | sandbox.py, sandbox_docker.py; disposable nonroot/rootless worker or stronger VM boundary, readonly root, no host home/socket/cookies, CPU/RAM/PID/output/wall quotas | Actual probes for symlink/junction traversal, mount/device/process abuse, forbidden file reads and timeout cleanup; not a universal escape-proof claim |
| Missing sandbox or malicious package import | plugins/worker.py isolates processes; integrity hash and reviewed manifest, no host imports or automatic pip/npm hooks | Missing backend fails closed; hash mismatch/update reapproval; package metadata does not prove trust |
| SSRF / covert egress | egress_policy.py network broker; deny by default; validate DNS/IP and redirects on every connection, IPv4/IPv6, loopback/private/cloud metadata; browser subresources, WebSocket and WebRTC coverage | Rebinding, redirect and proxy bypass probes; provider credentials only sent to pinned intended endpoint; OS/network isolation required, not URL validation alone |
| Cross-tenant memory/history leak | ACL before retrieval/join/ranking; scoped IDs for summaries, caches, vectors and source attachments | Two-account collision and delete/expiry/export tests; old shared FTS remains explicitly shared until migrated |
| Secrets in model/logs/results | secret_broker.py stores handles; inject at worker boundary, bounded structured logs, redaction/export policy and encrypted credential/backups | Canary secrets must not appear in provider prompts, tool output or audit metadata; pattern redaction cannot recognize every arbitrary secret |
| Replayed or spoofed channel events | channels/router.py verifies platform signature, timestamp/replay ID, immutable owning identity; scoped outbox | Real callback replay/signature tests; revoke disconnected installations; service credentials required |
| Duplicate external writes after crash | durable outbox plus intent ID and remote idempotency/reconciliation; task leases fenced | Crash before/after write then restart; ambiguous outcomes recorded for human review, never blindly replayed |
| Admin/effectful schedule escalation | scoped service identity and expiring capability, revalidate on every tick/tool; emergency stop fences all workers | Expired owner, changed args, shutdown mid-flight; queued tasks cannot retain stale privilege |
| Audit tampering / log failure | metadata HMAC chain and durable receipts; externally stored chain anchors where configured | Alter/delete/reorder tests and fail-closed on receipt failure; local key holder/root can forge local chain |
| Abuse through delegation or remote/container tools | child capability is subset of parent; SSH pinned host/user; broker container operations without mounting Docker socket in workers | Cross-agent permission widening and target change denied; tools limited to owned/authorized targets |
| Resource exhaustion / cancellation leaks | quotas and admission control; bounded parallelism, per-model queue, process-group cancellation, lease cleanup | Concurrency/flood/cancel/disconnect/restart tests; no unbounded token/tool loops |
| Training or skill poisoning | consented provenance, immutable candidate versions, scan plus isolated tests, frozen heldout, explicit review and rollback | Failed examples not treated as successes; no production code changes or live weight updates; original checkpoint hash unchanged |

## Approval and operation policy

Read-only search and low-impact tools may be allowed by a scoped policy. Writes, external sends, repository publication, remote execution, credential handling, security scans and destructive changes require the configured explicit approval; an approval for one action is not approval for arbitrary future actions. Cybersecurity tools require an authenticated authorized actor, explicit target/expiry, safe limits and a bounded supported tool. No malware deployment, credential theft or retaliation feature is in this design.

Default all new effectful tools off. External access stays loopback/closed until authentication, origin/CSRF, rate-limit, reverse-proxy/TLS and tenant tests pass. Prompt injection and sandbox tests are finite tests, not certification. Root compromise, unknown kernel/runtime vulnerabilities, malicious legitimate owner actions and external-service outages remain residual risks. Release notes must state tested environments and open findings.

Security acceptance owners: G01 policy/migrations, G02 isolation/egress, G04 lifecycle, G05 retrieval isolation, G07 supply chain/MCP, G08 delegation, G09 channel identity, G10 unattended execution, G11 remote/browser actions, G15 release audit. Exact test paths are in the file plan.
