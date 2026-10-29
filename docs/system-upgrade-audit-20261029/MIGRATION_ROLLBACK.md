# Integration, migration and rollback plan

## Preservation baseline

Keep the original production Git commit/tree, selected profile bytes/hash, model
identity manifest, base/adapter/tokenizer file hashes, training lineage, active
receipt and separate native source pins. Record actual service environment/lock
identities. Do not copy credential contents into reports or source control.

The audit baseline verified the existing identity
`182559bbb77dad2ac9f53be2252ef0fa8a3698851d8d47708d5264701170e13b`
before and after inference. It made no production source/configuration/database/
model migration. New audit documentation is separate from runtime implementation.

## Additive database policy

Use the existing Store and SQLite backup owner. Do not introduce a duplicate
memory database or alter positional legacy table layouts. The current platform
v1 SCHEMA/CHECKSUM must remain immutable. New components use their own migration
namespace, explicit version/checksum and operator-reviewed receipt. Reuse reserved
document tables only after real scope/retention APIs are implemented.

Proposed migration process:

1. Produce a dry-run manifest with exact old/new schema versions, statements,
   affected tables/indexes, size/locking estimates and rollback/compatibility tests.
2. Take an exclusive-new-path SQLite online backup using
   platform_repository.backup; integrity-check it. A raw copy that misses WAL is
   not a consistent backup. Back up encryption/audit keys separately under private
   operator control; a database backup alone cannot restore encrypted MFA/audit.
3. Validate restoration in a private test-owned environment, never expose real
   credentials or user data to an experiment worker. Fixtures/sanitized snapshots
   are distinct from private production rollback archives.
4. Obtain current owner/MFA approval bound to schema manifest, source/model/config
   identities, backup receipt, target and expected production revision.
5. Drain writers as required; revalidate the expected version and approval; apply
   one transaction with checksum receipt. On failure, rollback the transaction,
   retain evidence and keep the component disabled. No automatic schema reset.
6. Run integrity, legacy layout, scope, deletion, restart and API compatibility
   tests; only then enable the feature flag.

An older code revision may ignore component-owned additive tables if tested.
Do not automatically downgrade schemas or restore a stale full database over new
user writes. If compatibility is uncertain, disable/drain the component and use
an operator-reviewed forward repair or a maintenance-window restore with a stated
data-loss boundary.

## Per-change release checklist

- Default-off flags and optional-import tests leave existing install/chat working.
- Existing public signatures and response meanings are retained; additive API
  fields/routes are documented and still enforce server authentication.
- Native Hermes/OpenClaw/TradingAgents environments, source trees, state, sessions,
  credentials and risk workflows remain independently operational.
- A feature flag cannot silently enable a model, download weights, change context,
  merge adapters, run a tool, migrate production or grant a role.
- New executable capability/egress/image/toolchain policies receive explicit
  security review, exact-action approval tests and real backend acceptance.
- Model training uses a new candidate path from the verified trained parent.
  Failed quality/security/retention gates remain failed. Model/export compatibility
  alone does not approve deployment.
- Source releases, model references and profile updates are immutable/versioned
  and use expected-head/profile comparisons. Keep the previous known-good release.
- No silent Git commit/push, native action replay, cloud spend or external
  publication is triggered by untrusted model/tool/skill input.

## Rollback by subsystem

| Change | Reversible action | Data/effects to preserve |
| --- | --- | --- |
| Observer/proposal UI | Disable Evolution flag, stop admission, revert additive source release | Event/proposal/rejection history, audit anchors and migration receipt |
| Retrieval/semantic/graph | Disable index backend; use existing lexical/shared behavior where appropriate | Original source documents, ownership, approved memory and deletion tombstones; rebuild optional indexes from retained sources |
| Supervisor/tools/scheduler | Stop new tasks; revoke grants; cancel/drain owned workers; disable related flag | Durable intents, approvals, unknown native outcomes and delivery receipts; never replay uncertain effects |
| Browser/desktop/MCP/media sidecar | Stop its service and routing entry; preserve native backends | Private state as retention policy allows, approved artifacts, platform permissions; do not delete upstream source/state |
| Candidate code/config | Select approved previous release with expected-revision checks | Current user state; do not overwrite intervening configuration changes |
| Candidate adapter | Existing deployment.rollback with verified receipt/lineage and approved plan | Original base/adapter/tokenizer, previous profile, candidate/evaluation evidence; no weight reinitialization |
| Additive schema | Prefer older compatible code or forward repair; restore only in reviewed maintenance window | New user writes and private backup/key integrity; no automatic destructive downgrade |
| Unknown external effect | Mark needs_reconciliation; operator inspects native receipts/target | Cannot guarantee reversal or exactly-once replay; retain evidence and deny automatic retry |

## Deployment and reliability acceptance

Use a real operator-selected persistent host with sufficient storage/RAM, private
credentials/state, backups, firewall/egress rules, authenticated TLS/private access
and supervised services. Existing systemd units restart processes, but their timer
does not verify model readiness or long-running availability. The transient
execution workspace is not a 24/7 host.

Before any production claim: verify actual authenticated health/readiness, model
identity/inference, existing account/MFA, tenant/session/memory isolation, queue
capacity, rate/concurrency limits, cancellation/drain, interrupted effects, reboot
persistence, backup restoration, rollback and a specified measured soak/SLO.
Record host/resource/workload details, outage/recovery results and remaining
limits. Do not enable live trading or broker execution as a side effect of this
upgrade; those require their own account, limits, risk workflow and approval.
