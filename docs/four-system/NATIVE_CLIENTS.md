# Native clients: contracts and activation gates

PR #33 merged private inference and the original-account control plane at
`4ca2b760e72f01cb0f9b665ee9aab06f05f1f6b9`. This increment adds clients outside
all three original source trees. Zenith remains the default model. It does not
claim connected native runtimes, full parity, sandbox safety or successful
external delivery.

## Exact supported source contracts

| Component | Audited immutable pin | Source and behavior |
| --- | --- | --- |
| Hermes | `d05095663342556788cf2a198bfa7844cc7968ab` | `gateway/platforms/api_server.py`, `api_server_runs.py`, `api_server_run_idempotency.py`: authenticated `/v1/capabilities`, durable `/v1/runs`, native status and stop |
| OpenClaw | `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f` | `packages/gateway-client/src/device-auth.ts`, `packages/gateway-protocol/src/schema/frames.ts`, `schema/logs-chat.ts`, `src/gateway/server-methods/send.ts`: protocol 4, v3 device signatures, native chat events and actual channel send |

`target_source_pin` is the compatibility target, not remote binary attestation.
No service-provided version string proves source identity. Deployment must verify
the actual checkout/image separately. Neither upstream source is copied into
this package or patched. Their original licenses and state remain unchanged.
New Python bridge code retains Zenith's Apache-2.0 license. WebSockets 15.0.1 is
BSD-3-Clause; cryptography uses Apache-2.0/BSD-3-Clause and was already a Zenith
dependency. Keep dependency distributions' license files on redistribution.
Python 3.12, uv 0.12.23 and independent lockfiles remain required. The pinned
OpenClaw Gateway requires Node >=24.22.1 <25 or >=26.12.1 and pnpm 12.15.0;
source conformance uses Node 26.12.1. This does not install its full environment.
Hermes' audited managed runtime is Python 3.14 in a separate native environment.

## Destination files and operational behavior

- `integrations/runtime_bridge/src/zenith_integrations/hermes/api_client.py`:
  fixed loopback origin and dedicated native API key file; requires advertised
  authenticated durable admission. Requests model `zenith`, provider `custom`;
  checks the completed run's actual runtime, not the request echo. Unknown
  outcomes require native reconciliation. Stop acknowledges native control,
  not guaranteed termination of every subprocess.
- `hermes/session_bridge.py`, `hermes/event_mapper.py`: opaque HMAC-scoped
  account/conversation/profile sessions and distinct terminal outcomes. Never
  attach an existing CLI, desktop, ACP or messaging transcript.
- `openclaw/gateway_client.py`: integration-owned Ed25519 identity and manually
  paired native device token; no shared owner token fallback or automatic
  pairing approval. Uses the challenge timestamp and actual `backend` client
  mode. Requires exact effective operator read/write scopes and advertised
  methods, with no admin, pairing, approval or configuration RPC. One operation
  consumes each connection at a time; use a separate authenticated connection
  to request cancellation while waiting for a turn's terminal event.
- `openclaw/session_bridge.py`, `openclaw/event_mapper.py`: explicit native agent
  namespace, scoped session key and matching run/session/sequence. Partial
  output and admission are never success. Aborted local inference may still be
  finishing and remains labelled accordingly.
- `openclaw/channel_bridge.py`: native `send` RPC, never agent `chat.send`.
  Requires current original-owner verification plus a short-lived exact
  channel/recipient/report-SHA-256 grant. Admission is persisted before sending;
  a lost acknowledgement is never replayed. Late real receipts preserve the
  committed external result even when local cancellation races it. A callback
  must use the existing server-side MFA verifier, not model text.
- `shared/native_http.py`, `shared/redaction.py`: bounded loopback transport,
  dedicated private key handles, no redirects, no mutation retries, bounded
  responses, known-secret and sensitive-field redaction. These controls do not
  detect every possible unknown secret in natural-language native output.

Native profiles and origin/credential generations must remain fixed for an
admitted task. Credential/profile changes require stopping new admission and
reconciling pending native work first. Do not construct a new run after a timeout
or switch runtimes to repeat side effects. Generic Gateway RPC is a private
library implementation detail and is never exposed as an LLM tool or public API.

## Actual verification and explicit limits

Eight new executable client tests plus five existing bridge tests pass locally.
The fixtures emulate native protocols; they are not full native runtimes.
Additional source conformance imports the actual unchanged pinned TypeScript
`buildDeviceAuthPayloadV3` with Node and verifies all four Python-generated
signatures using Node crypto, including ASCII-only case folding. The measured
receipt is [openclaw-source-conformance.json](implementation-v0.2/openclaw-source-conformance.json).
Nine existing inference protocol tests also pass. The service CI repeats the
protocol tests and actual preserved-model SDK/account/job acceptance on Linux,
Windows and macOS. A dedicated source-conformance workflow checks the upstream
function without installing or altering its dependency manifests.

**Not verified:** real Gateway pairing, actual Hermes autonomous task execution,
native per-tool sandbox boundaries, channels, delivery, native full test suites,
24-hour availability or four-way financial workflows. No pairing token,
configured recipient, always-on operator host or verified isolation boundary
has been supplied. Public native execution remains unavailable. Do not expose
either native full agent using only the transport bearer key or paired device.
Hermes' public API explicitly executes tools on its API-server host. OpenClaw
operator write is not a per-tool filesystem/egress sandbox.

## Rollback

Stop only the additive bridge/client processes. Leave native runs with uncertain
outcomes available for operator reconciliation. Preserve private control state,
keys, pending receipts and native sessions. Deploy the previous bridge lock and
package version in its own environment; no original database migration, model
change or upstream patch needs reversing. The inference dependency advances to
bridge 0.2.0 without changing the inference protocol or original Zenith installer.
