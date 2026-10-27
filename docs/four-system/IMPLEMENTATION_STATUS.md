# Approved integration implementation status

The owner approved implementation after PR #32. The pinned audits remain
historical source evidence. The following implementation is additive; the
original Zenith `agent/` source and all three upstream trees are unchanged.

| Milestone | Current evidence | Remaining gates |
| --- | --- | --- |
| B0 separate distributions | `zenith-integrations` and `zenith-inference`, independent lockfiles and namespaces | Linux, Windows and macOS service CI passed in PR #33; remaining native environment CI |
| B1 control plane | Account-isolated durable jobs, original account/MFA verification, exact grants, persistent stop, audit integrity, restart reconciliation; real TCP job through Zenith | Native connector-specific scope/approval enforcement, reviewed report delivery, full operational deployment |
| B2 inference | Actual original checkpoint; OpenAI SDK model discovery/chat/stream/tool-result round trip, true token counts, disconnect recovery and optional bounded queue; four real concurrent requests answered correctly; hashes/profile unchanged | Broad native-agent task quality, all model families, remote TLS and hard supervisor limits |
| B3 Hermes | Public Runs API client: durable-idempotency discovery, submission/status/stop, actual Zenith attribution; protocol tests | Verified isolated native profile, full native runtime suite and real task acceptance; optional owner-scoped chat registration is implemented; full native acceptance is still pending |
| B4 OpenClaw | Protocol 4 paired-device client, scoped RPC, terminal events, exact approved report delivery ledger; signature bytes verified against original native TypeScript | Real paired Gateway, native runtime suite, isolated profile and approved configured-channel delivery; optional owner-scoped chat registration is implemented; full native acceptance is still pending |
| B5 TradingAgents | Separate pinned native research/backtest service; authenticated isolated jobs, owned worker cancellation, no order route; actual native LangChain provider called Zenith (37 input/2 output tokens) | Initial graph attempts encountered rate limiting and a 180-second deadline. With bounded queuing, the unchanged graph completed in 248.160 seconds: 17 measured LLM calls, 19,756 input and 1,113 output tokens. Generated reports contain quality issues and remain REVIEW; the real original owner/MFA bridge also completed in 239.510 seconds with all 17 native LLM calls and all roles present (PR #35 CI run 40428786900). Financial quality remains unverified. Point-in-time adversarial acceptance and paper ledger are not implemented |
| B6/B7 full platform | First real-model/account/job acceptance implemented | Full four-way tests, native regression baselines, isolated operator host, backups, hard limits and measured soak |

The [local measured acceptance receipt](implementation-v0.1/local-native-acceptance.json)
uses OpenAI SDK 2.54.0 and the unchanged trained model. It is a measured smoke
workload, not a speed improvement claim, financial result or feature-parity
certificate. A test-owned allowlisted arithmetic function supplies a tool result;
the inference endpoint itself executes no tools. Original profile and all
snapshotted model artifacts verify unchanged after the run.

The ordinary installer, current model selection, failed historical candidate
quality decisions, tokenizer, receipts, native sources and application routes are
preserved. No new training, model promotion, live order or external message has
been enabled. Remaining gates are not waived by the owner's implementation
approval.


[Local real queue acceptance](implementation-v0.3/local-queue-acceptance.json)
records four concurrent correct SDK responses plus original login revocation and
unchanged model/profile checks. This is not a financial quality measurement.
The new service has six contract/worker tests; the native SDK environment also
runs a counter-redaction test. Native financial measurements preserve failed
outcomes rather than promoting them. The Apple Silicon installer capacity failure was retried successfully; all 15
checks passed before PR #35 merged. Linux, Windows, and macOS service checks and
both macOS installer architectures passed.


## October 27 connection verification in progress

The optional Hermes and OpenClaw adapters now use the same original owner/MFA
lease enforcement as native financial research, exact message hashes, isolated
HMAC session identifiers, native admission receipts, bounded waits and explicit
cancellation reconciliation. Both remain disabled in default configurations.
The ordinary installer and model selection have not changed.

Measured locally: original Zenith suite 346 tests run (one platform skip), bridge
20 tests passed, inference service 13 tests passed, financial service 7 tests
passed. Checkpoint identity verification passed. These contract/regression tests
are not a substitute for running the separately installed native runtimes.

Hermes' authenticated API and TradingAgents' authenticated service started in
isolated temporary profiles. Hermes advertises durable run controls and no
enabled toolsets. OpenClaw's new private chat-only configuration passed the
actual pinned native Zod schema. Native build dependencies were installed in a
complete pinned checkout without upstream patches. Initial builds found a
missing generated workspace link, Node proxy setup, and the workspace's 8 GB
memory limit; those failures are retained as limitations, not passing evidence.
The lower-concurrency native build and real four-system acceptance are pending.
Temporary execution-session processes do not establish 24/7 production hosting.
