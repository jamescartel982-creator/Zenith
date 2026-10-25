# Operate the optional task pilot

Normal Windows/Linux installation and chat are unchanged. Use the existing
`install.py --mode local` and launch scripts. This pilot adds no runtime dependency
to the base installation and never enables itself on an existing installation.

## Enable for local review

Run from an updated checkout of the feature branch, after installing Zenith.
Keep the usual account login; an API bearer token alone is not an account or owner.

PowerShell:

```powershell
$env:ZENITH_PLATFORM_ENABLED = "true"
$env:ZENITH_PLATFORM_RUNTIME_ENABLED = "true"
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 serve
```

Linux:

```bash
ZENITH_PLATFORM_ENABLED=true ZENITH_PLATFORM_RUNTIME_ENABLED=true ./run.sh serve
```

These flags enable queued local text tasks. Restricted diagnostic tools still
require the separate `ZENITH_PLATFORM_TOOLS_ENABLED=true` flag, existing owner
elevation, enrolled/verified MFA and explicit short-lived capability grants. Never
put owner codes, authenticator seeds, cookies or API keys in chat or task inputs.
The reserved `ZENITH_PLATFORM_MEMORY_ENABLED` flag must remain false; enabling it
raises an unsupported-feature error. Existing personal memory needs no new flag.

The queued chat pilot needs an existing explicitly configured HF, Tiny, loopback
Ollama or loopback local-server provider. Queued ensemble/hybrid tasks are not yet
supported; ordinary chat keeps its existing provider. Do not replace a checkpoint
to enable this feature.

This stage is a programmatic API pilot; the current chat dashboard is preserved.
New task/approval panels are not yet provided. Keep external exposure disabled
until deployment-specific security/integration review is complete. The server's
existing public-bind bearer requirement remains in force.

## API

All routes below require the current account cookie and the existing server bearer
when configured. The existing same-origin change protection and security headers
remain. An absent/disabled platform returns 404 without creating platform tables.

| Route | Purpose |
| --- | --- |
| `GET /api/platform/status` | Enabled features, worker status, local provider compatibility and unavailable subsystems. |
| `GET /api/platform/tools` | Fixed diagnostic definitions and approval/MFA requirements; discovery is not permission. |
| `POST /api/platform/tasks` | Admit a local chat or explicit diagnostic plan; returns 202. |
| `GET /api/platform/tasks` | Latest 50 task summaries for the account. |
| `GET /api/platform/tasks/{id}` | Own request/result and exact-action approval records. |
| `GET /api/platform/tasks/{id}/events?after=0` | Scoped replay/SSE; reconnect using the last event ID as `after`. Streams periodically close to bound connection lifetime. |
| `POST /api/platform/tasks/{id}/cancel` | Idempotently request cancellation; an accepted effect may still require reconciliation. |
| `POST /api/platform/approvals/{id}` | Owner/MFA decision with strict `{"approved":true}` or false. |
| `POST /api/platform/authority/revoke` | Invalidate previously admitted platform actors/tasks for this account; preserve the login. |
| `GET /api/platform/audit/verify` | Owner/MFA-only chain check and anchor metadata. Store anchors independently. |

Example task bodies (send through your authenticated client, not model text):

```json
{"kind":"chat","message":"Explain how rain forms in one sentence."}
```

```json
{"kind":"diagnostics","steps":[{"tool":"sha256","arguments":{"text":"hello"}}]}
```

For network diagnostics, first activate the existing capability with a narrow
authorized target scope. Submit an explicit plan. When its status is
`waiting_approval`, review `request.steps[approval.step]`, including host/port, and
the stored tool/version and argument hash before approving. Approval cannot expand
the grant. A new session, changed arguments, expired/revoked grant or emergency
stop prevents execution. No arbitrary commands, URLs resolved to arbitrary hosts,
plugins or computer controls are accepted.

Responses include 400 for invalid/secret-bearing input, 401 for missing login or
server bearer, 403 for disabled/revoked execution, 404 for inaccessible task IDs,
413 for oversized new request bodies and 429 for queue/retention limits. Generic
task errors avoid persisting raw exception text. Poll task status instead of
assuming a queued request completed.

## Data, backups and rollback

Before enabling, stop the server and privately back up the existing data directory
and its keys. For live SQLite backups, `agent.platform_repository.backup` uses the
SQLite backup API and refuses existing destinations; copy protected MFA/audit keys
separately. Copying only a live `zenith.sqlite3` while omitting its WAL is unsafe.

The platform uses the existing database. New `platform_*` tables are additive.
`platform-audit.key` is stored as a private local file outside SQLite. If audit
history exists and the key is missing/corrupt, startup refuses to reset it. Restore
the matching key or disable the feature while investigating. Preserve external
anchor exports; a valid local chain alone cannot prove no suffix was deleted.

To roll back: stop admission, request cancellation and let the worker drain; stop
the server, turn off all platform flags, then use the previous application version.
Keep the new tables/key; do not drop old data or restore an older database over
new conversations. A whole-database restore needs an explicit reconciliation plan
for post-backup data. No checkpoint, tokenizer, adapter, saved provider or numeric
promotion gate needs to change.

Legacy owner emergency stop/revoke/lock controls remain authoritative for all new
tool executions. The model cannot mutate these controls. Status/unavailable fields
are deliberate; missing isolation or integrations never trigger a host fallback.

## Verify

```bash
python -m unittest discover -s tests -v
python -m scripts.smoke_platform
python -m scripts.platform_protection --output /private/new-before.json
python -m scripts.platform_benchmark --output /private/new-smoke.json --samples 3
python -m scripts.platform_protection --output /private/new-after.json --compare /private/new-before.json
```

Use the installed/activated Python interpreter, or the venv executable directly.
The native benchmark requires the **existing selected trained HF adapter** in the
local cache and runs offline with temporary data. It never downloads/replaces a
model or activates a candidate. Output destinations must be new and outside the
selected adapter/profile. Protection receipts include private profile hashes;
keep them private. The HTTP smoke uses temporary accounts and an owned loopback
server; its arithmetic response is a deterministic check, not a neural benchmark.

CI can supply `--bundle research_checkpoints/recovery-v1` explicitly when its
temporary install profile has no active adapter. This verifies/reconstructs that
existing inactive checkpoint in a new temporary directory for inference only,
requires the configured base-model identity to match, verifies bytes before/after,
and never saves activation settings or changes promotion gates.
