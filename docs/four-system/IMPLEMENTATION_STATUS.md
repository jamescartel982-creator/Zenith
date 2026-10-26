# Approved integration implementation status

The owner approved implementation after PR #32. The pinned audits remain
historical source evidence. The following implementation is additive; the
original Zenith `agent/` source and all three upstream trees are unchanged.

| Milestone | Current evidence | Remaining gates |
| --- | --- | --- |
| B0 separate distributions | `zenith-integrations` and `zenith-inference`, independent lockfiles and namespaces | Linux, Windows and macOS service CI passed in PR #33; remaining native environment CI |
| B1 control plane | Account-isolated durable jobs, original account/MFA verification, exact grants, persistent stop, audit integrity, restart reconciliation; real TCP job through Zenith | Native connector-specific scope/approval enforcement, reviewed report delivery, full operational deployment |
| B2 inference | Actual original checkpoint; OpenAI SDK model discovery/chat/stream/tool-result round trip, true token counts, disconnect recovery, hashes/profile unchanged | Broad native-agent task quality, all model families, remote TLS and hard supervisor limits |
| B3 Hermes | Public Runs API client: durable-idempotency discovery, submission/status/stop, actual Zenith attribution; protocol tests | Verified isolated native profile, full native runtime suite and real task acceptance; public execution remains disabled |
| B4 OpenClaw | Protocol 4 paired-device client, scoped RPC, terminal events, exact approved report delivery ledger; signature bytes verified against original native TypeScript | Real paired Gateway, native runtime suite, isolated profile and approved configured-channel delivery; public execution remains disabled |
| B5 TradingAgents | Original native unit baseline passed | New native service, real full graph/risk report, point-in-time adversarial acceptance and separately labelled paper ledger |
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
