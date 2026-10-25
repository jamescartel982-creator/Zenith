# Supervised platform pilot

This implements the storage/security foundation and a bounded gateway pilot from
the approved [OpenClaw integration plan](../openclaw-audit/README.md). It extends
Zenith main 0.15; it does not merge the separate reasoning PR #18, train a model,
change the selected provider, promote a candidate, or modify model artifacts.

## Implemented contracts

| Owner | Behavior |
| --- | --- |
| `platform_config.py` / `config.py` | Validated flags and quotas, all disabled by default; existing settings/defaults preserved. |
| `platform_migrations.py` / `platform_repository.py` | Version/checksum admission, transactional additive tables and consistent SQLite backups in the existing database. No legacy table changes. |
| `permissions.py` | Cookie-derived actor with session digest and account revision; live account/session checks. No prompt-defined roles. |
| `execution.py` / `tool_registry.py` | Adapter to the existing seven fixed diagnostics. Current owner, MFA, capability, scope, session and emergency checks before/after execution, plus platform fences at effect boundaries. |
| `approvals.py` | Network diagnostics wait for a one-use decision bound to task, step, tool/version, canonical arguments, account, session and expiry. Changed arguments require new approval. |
| `task_store.py` | Scoped admission, account/global capacity, deadlines, cancellation, worker leases, tool receipts and conservative recovery. |
| `event_bus.py` | Transactional task events and account-scoped replay; bounded asynchronous SSE polling. |
| `audit_chain.py` | Metadata HMAC chain, private key outside SQLite, startup/manual verification and exportable anchors. |
| `redaction.py` | Reject recognized credentials in persistent task input; redact recognized credentials and enrollment material from platform context/results before legacy turn storage. Heuristics are not a complete secret detector. |
| `runtime.py` | One supervised worker per app: existing local chat or explicitly supplied fixed diagnostic steps. Existing Agent model lock remains authoritative. |
| `gateway.py` / `server.py` | Opt-in authenticated routes, bounded request bodies and worker startup/drain through a preserved FastAPI lifespan. Existing routes and UI remain. |

`generate`/`stream`, provider construction, tokenizer, LoRA lineage, checkpoint
gates and training/export owners retain their current public contracts. The only
core extension is an optional trusted privacy-filter callback used by queued chat;
ordinary chat has the same default call signature/behavior. Provider tokens are
not passed to the model. Raw login cookies never enter task records, audit events
or model messages; the database's existing session digests support revalidation.

The pilot accepts local HF, Tiny, loopback Ollama and the existing loopback local
server configuration. Ensemble/orchestrated providers are not admitted to queued
chat in this stage; their existing chat/routing APIs still work independently.
Provider compatibility is not proof that weights/server endpoints are available;
actual inference can fail with a bounded task error.

## Lifecycle and persistence

`queued → running → completed | failed | cancelled | needs_reconciliation`

An authorized network step can transition from running to `waiting_approval`,
release its lease, then return to queued after a valid human decision. Completed
step receipts are reused within that task; approved action receipts are consumed
atomically with a durable tool intent before execution. No model generates or
modifies the submitted plan. Invalid/unknown tools and arbitrary shell are rejected.

After an expired running lease, recovery marks the task `needs_reconciliation`.
It never assumes a lost worker's external effect did not occur. There is no
automatic resume endpoint for uncertain tasks. Review the target/conversation and
receipts before deliberately submitting fresh work. Even read-only diagnostics
use this conservative policy. Cancellation during an uncertain effect also retains
reconciliation status; it cannot undo an already accepted effect.

All writes use `Store.connect()` and the same SQLite WAL database. Additive
`platform_*` objects do not change old positional insert layouts. The migration
checksum rejects unsupported/changed schemas instead of resetting data. Reserved
document tables are not an implemented private retrieval service: its flag is
rejected until that subsystem is built. Existing account memories, summaries and
shared corpus remain with their current owners and semantics.

## Bounds and limitations

- One runtime worker, eight explicit tool steps, 32 global/four account pending
  tasks, 120-second task deadline and 30-second renewable lease by default.
- Retained task capacity is 10,000; admission fails when capacity is reached.
  Retention cleanup is not silently performed. Task request/result data stays
  private to its account and occupies the existing data directory.
- New write bodies: 64 KiB/128 frames/five seconds before JSON parsing. Canonical
  data has byte, item and depth limits; event replay uses bounded batches.
- Deadline/cancellation is cooperative. Model loading and blocking provider calls
  can delay shutdown. A draining worker is not replaced with unrestricted host
  execution. CPU/GPU batching, hard process isolation and throughput tuning are
  not provided by this pilot.
- Audit capacity is bounded; failed receipt persistence prevents further effects.
  No automatic external anchor service is configured. Export anchors separately.
  HMAC history does not defeat a root attacker holding the key or detect an
  unanchored truncated suffix by itself.

## Explicitly unfinished

Structured model-generated tool turns, autonomous planning, sandboxed general code,
multi-agent execution, scoped semantic/project retrieval, executable plugins,
external skill packages, schedules/outbox, Telegram/Slack/Discord, browser/desktop
automation, new dashboard controls, tracing and an OpenClaw wire bridge are **not
implemented** here. Status reports them unavailable. No placeholder execution or
unsafe host fallback is installed. Existing chat, personal memory, model registry,
federation and reviewed training continue to work as before.

The historical audit/design documents label these future items as proposals.
They must not be read as acceptance evidence. See [operations](operations.md) and
[actual measurements](benchmark-results.md).
