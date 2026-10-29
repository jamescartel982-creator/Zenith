# Security findings and authorization architecture

This is a source/configuration audit and targeted regression review, not a
certificate that Zenith cannot be hacked. No unauthorized third-party testing,
malware execution or remote exploit attempt was performed.

## Verified current controls

- Normal passwords use Argon2id; account sessions are random, stored as hashes,
  expiring and account-bound. Owner bootstrap uses a generated high-entropy local
  code and a password KDF, not a hardcoded secret. See personal.py and admin.py.
- Owner elevation expires after 15 minutes. TOTP enrollment secrets are encrypted;
  verification uses a compare-and-swap step counter to prevent OTP reuse.
- ExecutionControls requires current owner elevation, verified MFA, explicit
  short-lived capability grants, scope and emergency-state checks. Literal-IP
  network diagnostics validate narrow CIDRs/ports and do not follow DNS redirects.
- Platform actors are derived server-side from live sessions and revisions.
  Exact-action approvals bind canonical tool arguments, task/step, account/session
  and expiry. Durable intents/receipts protect against unsafe replay.
- The existing HTTP middleware checks Host, browser cross-site requests, ambiguous
  lengths, request-size and body deadlines. Cookie protection, CSP, secret input
  filtering and sanitized validation errors are implemented. Login attempts are
  bounded. These controls do not constitute comprehensive DoS protection.
- Linux sandbox Python is default off and requires reviewed local image identity,
  unprivileged/no-capabilities execution, no network/host mounts, read-only root,
  cgroup/PID/time/output bounds and confirmed cleanup. It has no host fallback.
- The native inference/bridge/trading services require separate service identities
  and keys; a service key cannot authenticate as the Zenith owner. Native memory,
  credential stores and upstream source trees remain separate.
- Platform audit records form an HMAC chain with a private external key. The
  original application/admin/execution logs are not all covered by that chain.

## Findings: observed gaps, not invented exploits

| ID / priority | Evidence | Risk and implementation-ready action |
| --- | --- | --- |
| S1 / P1 assurance | Fresh pip-audit exited zero while exact CPU Torch was skipped; dependency-advisories.json | Completeness is not enforced. Add explicit scanned/skipped coverage gates and reviewed vendor mapping; scan integration/JS locks independently. Do not ignore advisories. |
| S2 / P1 publication control | GitHub main branch API reported protected=false at audit time | Require CI/review and restrict direct publication before Evolution writes. Changes to repository settings need owner administration access and explicit deployment policy; no settings changed here. |
| S3 / P2 evaluation integrity | quality.py:47; fresh plural-unit and JSON-whitespace mismatches | Version/validate scorers and preserve historical raw results. Weak grading can misdirect training, confidence and promotion decisions. |
| S4 / P2 production availability | server.py uses one Uvicorn worker without a configured global HTTP concurrency quota; login limits/task quotas cover narrower paths | Add measured admission limits/reverse-proxy controls before external access; test slow bodies, concurrent streams and fairness. This audit did not demonstrate a DoS exploit. |
| S5 / P2 audit integrity | audit_chain.py and docs/platform/architecture.md explicitly require external anchors | Unanchored suffix truncation or an attacker holding host keys cannot be excluded. Add approved off-host anchors/verification; do not call all logs tamper-proof. |
| S6 / P2 persistence operations | task_store.py, runtime.py, platform migration tables; quotas eventually refuse further work | Add explicit owner-reviewed retention/export/archive, capacity alerts and restore drills. Do not delete unknown-effect receipts or silently purge private task data. |
| S7 / P2 deployment evidence | deploy/four_system/services.py reports readiness_verified=false | Liveness timer is not authenticated readiness/24-hour soak. Add readiness and recovery acceptance on a real persistent host before an availability claim. |
| S8 / P2 reproducibility | Settings.revision defaults to main when setup/profile pin is absent; installed profile here is pinned | Require exact verified identity for protected experiments/deployment and warn on floating direct-use defaults. Do not force a default-model revision onto user-selected custom models. |
| S9 / P2 documentation | Older model-compatibility and activation snapshots predate implemented sidecars/later successful native CI | Add a current source-backed status index; retain dated history without presenting obsolete failure/pending status as current fact. |

S1/S2/S3/S7/S8/S9 are demonstrated coverage/configuration/documentation behaviors.
Other rows describe source-visible operational limits. None establishes a
confirmed remote compromise. Windows private-file protection relies partly on
operator NTFS ACLs; Unix mode checks do not prove Windows ACL safety. Encryption
at rest, backup key handling and host hardening require a deployment threat model.

## Trust boundaries and threats

| Input/boundary | Threat | Required control and tests |
| --- | --- | --- |
| Prompt / retrieved source / feedback | Prompt injection, forged role or approval | Treat as data; derive actor only from authenticated server; deny tool activation by text; replay/role-spoof tests. |
| Model-to-tool proposal | Unknown tool, mutated arguments, fake scope | Strict bounded schema; registered server-owned capability mapping; immutable action hash; revalidate just before effects. |
| Child agent / collaboration | Permission laundering, cross-project data | Intersect delegation grants; separate task/artifact ACLs; no inherited owner authority or credentials; cross-agent/tenant tests. |
| GitHub/repository/test suite | Malicious tests, hooks, traversal, credential theft | Exact baseline, approved path manifest, hooks disabled, untrusted execution in reviewed isolation; no host secrets or writable production mount. |
| Browser / desktop / media | SSRF, secrets in pixels, injected page instructions, unintended purchases/actions | Isolated service, target/window scopes, egress restrictions, bounded parsing and exact sensitive-action approval; no credential sharing. |
| MCP / skill package | Arbitrary process startup, schema/result injection, malicious dependencies | Official protocol validation; trusted registry and integrity review; isolated stdio; approved origins/auth; no self-registration or host shell. |
| Experiment / training dataset | Gate editing, leakage, malicious samples, unlicensed data | Frozen controller/scorers, disjoint data, source hashes, explicit rights/consent, retention tests and model-lineage validation. |
| Native runtime / broker | Duplicate effects, stale owner grants, unconstrained orders | Keep native policies/state; exact scopes and receipts; unknown outcomes require reconciliation. Live orders remain absent/disabled. |
| Observer / logs | Private data/secret leakage, misleading metrics | Metadata allowlists, redaction, tenant checks, bounded cardinality/retention; unavailable metrics stay unavailable. |
| Release / rollback | Stale approval, irreversible migration, overwritten user state | Expected revision/hash CAS, one-use owner approval, preserved previous release, compatible migrations, restore/reconciliation tests. |

## Central authorization extension

Reuse current Permissions, AdminStore, OwnerMFA, ExecutionControls and Approvals;
do not invent a prompt administrator code or competing credential database.
Current user/owner separation is implemented; generalized role administration is
an extension, not a current claim.

Proposed roles are ordinary user, scoped operator, evaluator, model-training
operator and owner. A role is a server-side policy binding, not a model label.
Service identities and specialist agents receive narrowly scoped machine
capabilities only. Default deny wins; child delegation cannot exceed the live
parent grant, tool policy or target scope. Capabilities include separate read,
proposal, experiment, tool execution, training, approval, migration and deployment
actions. The engine/model never receives approval/grant-management capability.

Every sensitive operation must check: current session and role revision; owner
elevation/MFA where required; feature enabled; active capability; exact target;
human approval if necessary; budget; emergency stop; matching arguments/version;
durable intent and audit capacity. Recheck after effects and do not release a
worker slot while its process still runs. Cooperative cancellation is not a hard
kernel/GPU termination guarantee.

Keep secrets in existing private handles or an approved secrets manager. Do not
embed them in prompts, source, tests, proposal records or model-visible errors.
Experiment/browser/MCP/desktop workers must not inherit owner codes, MFA keys,
cookies, broker keys, cloud/GitHub credentials or arbitrary environment variables.
Their dedicated service keys do not grant arbitrary network egress or owner role.

Emergency stop blocks admission/new effects, revokes grants and cancels/drains
owned work. It retains uncertain receipts and does not promise to undo an already
accepted external action. Explicit owner/MFA resume leaves old grants disabled.
Security policy changes and additional execution agents remain default off until
their backend, denial tests and human approval path pass.

## Required security acceptance before new external access

Run real fixture-based tests for expired/revoked sessions, MFA replay, scope and
argument mutation, cross-account resources, malicious tool/skill/page content,
secret redaction, dependency coverage, resource exhaustion, egress restrictions,
restart/cancellation and approval replay. Confirm actual sandbox behavior on the
supported host. Report tested containment limits; do not claim universal sandbox
escape resistance. Independently review new plugin, malware and desktop surfaces
before enabling them. No risk score or general quality improvement can waive a
failed authorization or protected-artifact gate.
