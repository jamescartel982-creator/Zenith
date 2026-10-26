# Independent native TradingAgents service

This package executes the unchanged pinned TradingAgents graph in a separate
Python 3.12 service environment. Zenith is the fixed quick/deep model through its
new authenticated inference API. It does not replace either model or native
graph. Source pin: `e8f5503e9b86d5c2710b0c76b1f686703968c9df` (Apache-2.0).
Preserve the native checkout's license and dependency notices. Never install
its dependencies into the original Zenith, Hermes or OpenClaw environment.

```bash
git clone https://github.com/TauricResearch/TradingAgents.git ../TradingAgents-native
git -C ../TradingAgents-native checkout --detach e8f5503e9b86d5c2710b0c76b1f686703968c9df
uv sync --project integrations/trading_service --frozen --extra native
uv run --project integrations/trading_service --frozen --extra native zenith-trading init --directory "$HOME/.local/share/zenith-services/trading" --source-root ../TradingAgents-native --inference-key-file "$HOME/.local/share/zenith-services/inference/tradingagents.key"
uv run --project integrations/trading_service --frozen --extra native zenith-trading serve --directory "$HOME/.local/share/zenith-services/trading"
```

First initialize and start the [separate inference service](../inference_service/README.md)
with `serve --queue-size 4` for the native parallel analysts.
The private research service binds only `127.0.0.1:8783`. Its newly generated
`bridge.key` authenticates a trusted service, not an end-user or administrator.
Never put it in prompts, source control, logs or an untrusted browser. The bridge
will continue reporting TradingAgents unavailable until its account-aware
connector, deployment and native financial acceptance gates are completed.

API requests use `Authorization: Bearer <private bridge.key>`:

- `GET /healthz`: pinned checkout/distribution/dependency readiness and stop state.
- `POST /v1/jobs`, stable `Idempotency-Key`: `account_id`, `operation` (`research`
  or `backtest`), `tickers` and canonical historical `dates`. One research cell,
  at most four backtest cells, stock assets only. Public inputs cannot override
  model, endpoint, native config, filesystem path or credentials.
- `GET /v1/jobs/{id}?account_id=...`: account/service-scoped status and report.
- `POST /v1/jobs/{id}/cancel?account_id=...`: cancel owned work, await worker exit.
- `POST /v1/control/stop`, `/v1/control/resume`: trusted-control service capability;
  stop persists, cancels owned jobs and never replays jobs on resume/restart.

Only a trusted bridge service may act on behalf of `account_id`; this key is not
a multi-user login system. Do not expose the service directly to end users.
Original Zenith MFA/session checks belong to its public bridge, which has not
registered this backend yet. Native read-only market-data tools execute under
the service OS identity. An owned process group and time limit are not an OS
sandbox or network-egress firewall. Use a separately isolated deployment before
external access. Windows child-process-tree isolation is not yet verified.

All four native analysts, both research debaters, Research Manager, Trader,
three risk debaters and Portfolio Manager remain in the native graph. New
reports preserve their evidence, label missing stages/rating `REVIEW` and leave
calibrated confidence null. `job.status=succeeded` means the worker returned a
report; its independent `workflow_status` can still require review. It never
promotes a model or clears a financial quality gate.

The native backtest scores independent dated decisions using its original
point-in-time guards and settlement; it is not a simulated brokerage account.
Complete vendor publication-time auditing and model training-knowledge leakage
have not been verified. No paper-fill ledger is implemented in this increment.
There are no live orders, broker credentials, order routes or automatic messages.

Each account/service pair gets its own native cache/memory, per-job reports and
checkpoints in newly owned state. Original native memory/data are untouched.
Native SDK inference retries are bounded at three for parallel analysts sharing
the single-generation inference endpoint; whole jobs and side effects are never
retried automatically. Partial runs stay available for manual reconciliation.
Native provider exceptions are not returned to API clients because they can
contain secrets, complete prompts or upstream bodies.

Local contract/lifecycle tests use an explicit test executor. CI separately runs
the actual native LangChain provider against Zenith's preserved checkpoint,
then measures an actual bounded native financial graph job. Its artifact records
whether all roles completed; a completed infrastructure test is not a claim of
financial accuracy or successful full-graph acceptance. No current financial
benchmark improvement is claimed. See `docs/four-system/IMPLEMENTATION_STATUS.md`.

Rollback: stop only this service and retain owned account state, native reports,
checkpoints and audit ledger for reconciliation. No native source changes or
original database migrations require reversing. Do not silently restart a
partially completed financial job or delete its checkpoint to force a fresh run.


The measured first native provider call returned `4` with 37 input and 2 output
tokens. The first full graph encountered single-model admission rate limiting;
the optional queue addresses that integration mismatch. A subsequent CPU graph
hit its explicit 180-second deadline, so full financial acceptance remains
unverified. The instrumented probe uses a 600-second native-job budget and
records native LLM callback counters without persisting messages or hidden
reasoning. Missing usage is represented by the count of responses with measured
usage; zero known tokens does not prove zero total consumption. Tool/network
latency and full financial quality are not inferred from these counters.
Native dotenv loading is disabled only in this new worker profile so unrelated
parent `.env` credentials cannot be imported. Original native launch behavior
and source are preserved.
