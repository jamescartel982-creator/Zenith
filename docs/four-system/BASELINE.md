# Baseline and verification boundaries

Before these changes, Zenith at `c0760cbf47a25dc8fb4f9a4f6452a020f8b1c037`
ran 340 tests in 67.326 seconds: 339 passed and one platform-specific test skipped.
The raw log is in `evidence/zenith-baseline.log`.

The `Pinned TradingAgents native baseline` workflow checks out upstream commit
`e8f5503e9b86d5c2710b0c76b1f686703968c9df` unchanged, builds from a disposable
copy and runs the original default non-integration test suite. Dependencies are
hash-locked for Linux Python 3.12 in its own environment. Upstream test fixtures
isolate native state and reject external network calls. No provider or broker
credentials are supplied. Source preservation is checked after tests.

These native tests include scripted-model graph workflows and historical-data
boundaries. They **do not** prove a real Zenith-backed analysis, calibrated
confidence, all-model point-in-time knowledge, operational Hermes/OpenClaw
bridges, authorized messaging delivery, paper fills, a production sandbox or
24/7 availability. Those remain separate acceptance gates in `ACCEPTANCE.md`.

The native runtime environments are not merged into Zenith's requirements.
Apache-2.0 upstream source and license stay unchanged. Existing Hermes/OpenClaw
source audits were reused at the same pinned commits; their complete native
runtime suites have not been run in this new baseline workflow.

See the pull request checks for actual results and the dated validation receipt
added after runs finish. A failing baseline must be recorded, not hidden by
rewriting upstream tests.

## Measured native baseline, 2026-10-26

[GitHub run 40284298753](https://github.com/n8storm/Zenith/actions/runs/40284298753)
passed the original suite: **1,361 passed, one skipped, one deselected**, in
**18.07 seconds** of pytest time. The skip is optional AWS Bedrock support
(`langchain_aws` absent); the deselected integration test requires external
services. All tracked native source stayed unchanged. The selected test-output
receipt is `evidence/tradingagents-native-baseline.log`; the workflow artifact
contains the full console output and JUnit XML. This result does not satisfy the
separate real-Zenith or messaging acceptance gates.

The current local Zenith suite ran **346 tests**, with **345 passing and one
Windows-specific skip**, in **58.802 seconds**. Focused Mac platform tests also
passed after making launcher fixtures independent of an existing checkout venv.
The real preserved research checkpoint loaded and returned `4`; tokenizer semantic
fingerprint remains `221ea68122dfcfb2772276b69e62fc97ea9b13785ee069b118ee36498b19a418`.
The checkpoint probe reports `production_profile_changed: false` and
`restricted_tools_enabled: false`. No financial-return or latency improvement is
inferred from these software regressions.
