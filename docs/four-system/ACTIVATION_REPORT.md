# Four-system activation and verification

This report distinguishes runtime communication from answer quality and full
feature parity. Zenith's original checkpoint, tokenizer, architecture, adapter
lineage and production data are preserved. No training or promotion occurred.

| System | Measured evidence | Limits |
| --- | --- | --- |
| Zenith | Original checkpoint identity verified; real SDK chat/stream/tool-result tests and original account/MFA regressions pass | Existing experimental adapter quality decisions are preserved |
| Hermes | Owner-approved isolated chat build; actual answer `4`, served `custom/zenith`, 620 input / 2 output tokens, 9.777 seconds; 21 untouched native context tests pass | Chat only; actual 8,192 served / 32,768 architectural context; tools disabled; broader native parity unverified |
| OpenClaw | Exact pinned native build; real paired read/write device; original owner/MFA bridge to Zenith completed in 22.563 seconds, 2,605 input / 8 output tokens; logout revoked access and hashes stayed unchanged | Native answer echoed a context placeholder, so answer quality failed. Raw output is preserved and flagged for review; slash text/URLs are refused in the least-privilege chat route |
| TradingAgents | Pinned native analyst/researcher/risk/portfolio graph completed with all roles; original owner/MFA bridge measured 17 calls, 19,756 input / 1,113 output tokens in 239.510 seconds | Reports remain REVIEW; financial accuracy, full point-in-time publication validation and paper portfolio accounting are unverified; no live-order route |

The combined four-runtime test starts all four independently maintained services,
checks actual authenticated readiness, exercises the original owner/MFA grants,
submits one account-isolated job per runtime, checks duplicate admission and
logout revocation, and verifies unchanged model artifacts. Its report records
blocked/failed workflows explicitly and separates model-quality flags from
control-flow completion. It is not a feature-parity or financial certificate.
The first combined run passed on the larger CI runner: all four authenticated
runtimes connected, all four jobs completed, duplicate admission was prevented,
logout revoked access and original model hashes stayed unchanged. The measured
times were Zenith 0.438s, Hermes 4.241s, OpenClaw 17.271s and TradingAgents
184.753s. TradingAgents completed all 17 model calls with 19,756 input and 1,113
output tokens. This is a measured workload, not a performance improvement claim.
See [the combined receipt](implementation-v0.4/four-system-native-acceptance.json)
and [CI run 40534098000](https://github.com/n8storm/Zenith/actions/runs/40534098000).
The latest-head regression checks must still pass before merge.

Evidence: [Hermes native receipt](implementation-v0.4/local-hermes-chat-acceptance.json),
[OpenClaw native receipt](implementation-v0.4/native-openclaw-acceptance.json),
[Hermes compatibility build](../../integrations/hermes_compat/README.md),
and [bridge setup/permissions](../../integrations/runtime_bridge/README.md).

## Operator activation

All optional routes remain unconfigured by default. Use the separate pinned
runtime environments, explicit native profiles, dedicated generated internal
credentials and already-paired OpenClaw device described in the bridge README.
Enable the approved Hermes compatibility policy only in its separate copy and
supply its exact manifest to the bridge. Never inflate model context or grant
Gateway administrator scope merely to make a chat test pass.

The original owner still signs in, elevates and verifies MFA through Zenith's
original account system. Each native job needs a short-lived exact task grant.
A service credential is not an owner grant. The test harness creates separate
test-owned accounts; it does not bypass or replace an existing owner's MFA.
Default inference remains Zenith. Native memories and credentials are separate.

## Persistent hosting

The current workspace has an 8 GB memory limit and approximately 161 MB free on
its disk-backed filesystem. Temporary runtime dependencies were placed in a
memory-backed filesystem; a complete native build and co-resident Gateway/model
exceeded that limit. Exact-pin builds and full native acceptance therefore run
on the larger GitHub runner. Temporary workspace processes stop when its session
restarts; they do not constitute a 24/7 deployment.

A persistent operator-selected host, durable storage, supervised services,
backups and a measured soak are still required before a 24/7 availability claim.
A starting sizing estimate is at least 16 GB RAM and 20 GB free disk for this
CPU configuration; that is not a measured capacity guarantee. Existing normal
Windows/Linux/macOS installation remains unchanged. No paid host was created.

Rollback: stop the additive bridge and compatibility process, retain native
receipts/state, remove the optional configuration from an archived copy, and
restart the original pinned native runtime. No original model migration is needed.
