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
21 tests passed, inference service 13 tests passed, financial service 7 tests
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


Actual Hermes execution failed during native agent initialization: the custom
provider requires 64,000 context tokens, while the unchanged Zenith model has
32,768 architectural positions and the sidecar serves 8,192. Authenticated API
availability does not establish compatibility. The bridge now checks actual
inference context metadata and reports this route blocked before submission.
No window was inflated, model changed or upstream guard patched. The separate
chat-only compatibility proposal is unapplied and awaiting an owner decision.
Local regression results remain passing; the native full-build retry also
exceeded 8 GB and was killed. Exact-pin native build is running in GitHub CI.


Exact-pin OpenClaw build completed in GitHub run 40438313498, with the native CLI
reporting `OpenClaw 2026.10.7 (2f5727b)`. All 20,800 generated artifact files were
hash-verified on retrieval. The unmodified Gateway booted here and a dedicated
Ed25519 device reconnected using only `operator.read`/`operator.write` and native
`device-token` authentication; actual authenticated health passed. The shared
owner credential stays outside the bridge. Original complete audited source is
retained; only the disposable deployment checkout uses Git sparse checkout to
reduce memory-backed storage use.

Actual chat testing found a privileged-field mismatch: native
`suppressCommandInterpretation` requires admin. The client no longer sends that
field, never elevates its scopes, and conservatively refuses slash-containing
text before mutation. Native WebChat ignores `commands.text:false` for some
commands, so that setting alone is not relied on. A subsequent local turn was
admitted but stalled under memory pressure; cancellation acknowledgement was
uncertain and the native receipt was retained for reconciliation. This is not a
successful native model turn. Real paired Gateway + model + original owner/MFA
acceptance now runs on the larger CI host; results are pending.


The owner approved the isolated Hermes compatibility build. Its actual native
chat completed in 9.777 seconds with answer `4`, 620 input / 2 output tokens and
served `custom/zenith` metadata from the actual post-turn agent. The original
native context regressions passed: 21 tests. All 24 bridge tests (before the new
context-echo case) and 13 inference tests pass. Original upstream source remains
unchanged; only a new exported compatibility copy has context/capability/runtime
metadata changes. See `implementation-v0.4/local-hermes-chat-acceptance.json`.

Real original owner/MFA -> paired OpenClaw Gateway -> Zenith inference passed in
CI run 40530613574: 22.563 seconds, 2,605 prompt / 8 output tokens, logout
revocation and unchanged source/model hashes. **Answer quality did not pass**:
the native output echoed an interrupted-input context placeholder instead of
answering the arithmetic question. This is a functioning transport/control-flow
integration, not verified task competence. The bridge preserves the raw native
output, flags this known context echo for review and never marks it a verified
answer. Full four-way workflow acceptance is now being measured separately.


Combined acceptance passed in CI run 40534098000 (source head d2c17a8): all four
runtimes connected simultaneously; actual jobs completed through original
owner/MFA controls; all duplicate submissions resolved to existing jobs; logout
revoked bridge access; model artifacts remained unchanged. Measured times:
Zenith 0.438s, Hermes 4.241s, OpenClaw 17.271s, TradingAgents 184.753s. Native
financial graph: 17/17 completed model calls, 19,756 input / 1,113 output tokens,
all native roles complete, rating REVIEW. This verifies the restricted runtime
connections and workflow control flow, not full model competence or feature
parity. The later context-echo flag and export-path guard are separately covered
by 26 bridge tests. The actual combined receipt is published under
`implementation-v0.4/four-system-native-acceptance.json`.

Cancellation review follow-up: the previous head 699131e passed all sixteen CI
jobs, including the real combined four-runtime acceptance (run 40537940441).
Review identified two additional uncertainty windows: owner cancellation while
a native admission response is in flight, and failure to confirm native
termination during cleanup. Both adapters now classify interrupted admission as
requiring reconciliation instead of confirmed cancellation. Cleanup remains
shielded from repeated cancellation, has a 15-second budget, and normalizes
unconfirmed termination failures to UnknownExecution while retaining any
persisted admission receipt. There is no automatic replay or native-state
deletion. Four focused regression tests cover both admissions, Hermes stop and
status failures, independent OpenClaw control-connection failure, repeated
cancellation and cleanup timeout. Fresh CI results are required before merge.
Rollback is the additive bridge revision only; native trees and model artifacts
are untouched.


OpenClaw answer-quality follow-up (native evidence pending): a separate opt-in
provider plugin now uses the pinned public SDK replay-policy hook for local
`zenith/zenith`. The hook retains standard OpenAI-compatible sanitation and
selects current-turn context rather than exact-entry prefix-cache retention.
Native acceptance now fails unless addition, multiplication and exact-word
instruction cases answer correctly, and the empty interrupted-input snapshot
is absent from measured model calls. Known context-echo detection remains on.
32 bridge regressions and two Node policy tests passed locally; native SDK
loading and actual-model quality require the fresh pinned-runtime CI result.
No upstream source, model weights, adapters, live-order routes or credentials
were changed. Live brokerage and permanent hosting remain blocked on operator
broker/risk details and hosting access respectively; review approval alone does
not provide either connection.


Native trial 40606994974 failed its new arithmetic gate: the empty interrupted
snapshot was no longer the answer, but the model echoed the temporal context.
The fix is not considered verified or mergeable from that run. The plugin now
also uses the public native stream-wrapper hook to move only producer-tagged
trailing runtime carriers before the active user, retaining all content/roles,
tool compatibility and cancellation. No textual provenance is trusted. Five
Node policy regressions pass. Native acceptance records and checks that the
actual current question is the last model message; all three frozen cases
must pass before answer_quality_verified can become true. Fresh CI is required.
