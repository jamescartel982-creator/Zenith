# Zenith runtime bridge 0.3

An independent control-plane package. The first implementation connects real
Zenith inference to the unchanged Zenith account/session API. Hermes, OpenClaw
and TradingAgents remain preserved native sources, and are reported disconnected
until their connectors and isolated profiles pass their own acceptance gates.
No placeholder response is substituted for a missing runtime.

Install Python 3.12 and pinned `uv 0.12.23` separately. Do not merge this package's
lock or dependencies into the original application or native runtime manifests.

```bash
uv sync --project integrations/runtime_bridge --frozen
uv run --project integrations/runtime_bridge --frozen zenith-bridge init --directory "$HOME/.local/share/zenith-services/bridge" --inference-key-file "$HOME/.local/share/zenith-services/inference/operator.key"
uv run --project integrations/runtime_bridge --frozen zenith-bridge serve --directory "$HOME/.local/share/zenith-services/bridge"
```

Use private user-profile directories on Windows and protect their NTFS ACLs.
Run the existing Zenith account server separately, normally at
`http://127.0.0.1:7860`, and the new inference endpoint at
`http://127.0.0.1:8781`. The bridge defaults to port 8782 and fixed loopback
origins. Initialization accepts explicit alternate loopback origins and an
optional owner-only `--zenith-access-token-file` when the original app has a
server access gate. This handle is forwarded only to that original origin;
service/model credentials and owner access remain separate.

The operator logs in through the original Zenith API. Bridge requests carry its
`zenith_login` cookie; no new password database is created. The bridge checks the
current account at the original API on every request and again before starting
work. It never forwards the login cookie to the model or native runtimes.
Cross-origin browser access is disabled; this release is an API/CLI control plane,
not an existing web UI redesign.

- `GET /healthz`, `GET /v1/runtimes`: authenticated control/readiness status.
- `POST /v1/jobs`: explicit runtime/operation/payload, stable `Idempotency-Key`.
- `GET /v1/jobs/{id}`, `GET /v1/jobs/{id}/result`: account-owned state/result.
- `POST /v1/jobs/{id}/cancel`: cancel owned work; never silently replay it.
- `POST /v1/grants`, `DELETE /v1/grants/{id}`: owner elevation **and verified MFA**;
  short-lived exact capability/scope grants bound to the original login.
- `POST /v1/control/stop`, `POST /v1/control/resume`: MFA-protected persistent stop;
  all grants are revoked and are not restored on resume.

The current supported job is `runtime=zenith`, `operation=chat`; its payload uses
the inference chat contract and returns a complete response. Streaming is provided
by the direct inference API. Other runtimes fail unavailable, not success. Live
orders are not an allowed operation. Model output cannot mint credentials,
capabilities, native sessions or new runtime registrations.

The new private SQLite ledger stores control state, bounded job results, grants
and an authenticated audit chain. It does not open/migrate native memory stores.
Idempotency is account-bound across logins; conflicting request reuse is denied.
Incomplete jobs are marked interrupted after restart, never automatically
replayed. Native external effects will need separate reconciliation and native
acknowledgements when connectors are implemented. Local keyed audit integrity
detects edits; it is not remote anchoring or protection from the host owner who
can read the key or truncate all local state.

Job output is private operational data, not a second conversation-memory system.
Keep this control directory separate, protected and backed up according to your
retention requirements. The original accounts, conversations, training records,
MFA and native memories remain in their original locations.

Rollback: stop only this new bridge, retain native state/weights/receipts, and
remove or archive only its owned environment/configuration/control ledger. Its
emergency stop persists in that ledger. No original public API has changed.


## Native clients (optional, gated)

`uv sync --project integrations/runtime_bridge --frozen --extra native` adds
WebSocket 15.0.1 without installing or replacing either upstream runtime.
See [native client contracts](../../docs/four-system/NATIVE_CLIENTS.md).
These library clients are not registered as executable public bridge backends;
`/v1/runtimes` continues to report them unavailable until isolated native
profiles and full acceptance are verified. Transport authentication alone does
not authorize a native agent's filesystem, shell or network access.


## Explicit read-only native financial research

Once the independent [TradingAgents service](../trading_service/README.md) is
installed and running in a verified private environment, initialize a **new**
bridge profile with `--trading-origin http://127.0.0.1:8783`,
`--trading-key-file <native service bridge.key>` and `--job-timeout 600`.
These options are empty by default and never overwrite an existing profile.
Only read-only `research` is connected through the bridge. Paper trading,
backtest promotion and live orders remain disabled on this route.

The original owner must log in, elevate and verify MFA, then explicitly request
`jobs.submit.tradingagents` with scope `runtime=tradingagents`,
`operation=research`, `ticker=<exact symbol>`, `as_of=<exact date>` and a lifetime
of at most 300 seconds. Submit that grant ID in a `tradingagents/research` job
with payload `{"ticker":"AAPL","as_of":"2025-01-17"}`. The caller cannot supply
an account ID, credential, model or URL. The server binds the native job to the
verified owner and persists its receipt. Grant/session revocation and emergency
shutdown cancel the owned native job; uncertain termination is labelled
interrupted and requires reconciliation, never replayed. Grants authorize a
bounded execution window; their expiry cancels jobs still in progress.

A completed job can contain unreviewed or poor model output. Its native rating
is preserved for inspection, while the actionable rating remains `REVIEW`.
Protocol echoes are flagged; no calibrated financial accuracy or full source
publication-time validation has been demonstrated. Never use this connector as
an order signal. Neither a successful workflow nor its transport credential is
an administrator grant for other tools.

Hermes/OpenClaw clients remain optional libraries pending their actual paired,
isolated native runtime acceptance. Merely setting a URL does not activate them.
