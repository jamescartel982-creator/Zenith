# Feature parity report

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

**Full parity is not achieved or claimed. This delivery is an audit and review proposal.** Zenith main has its existing model/chat, provider orchestration, owner controls, memory, training/evaluation and deployment infrastructure; PR19 adds a default-off supervised task pilot, not an autonomous replacement agent. Neither open PR is treated as merged. The source audit does not itself implement any of the new unified features.

| Status | Coverage records |
| --- | --- |
| PARTIAL | 33 |
| NOT STARTED | 2807 |
| BLOCKED | 832 |

These are overlapping coverage records, not independent-feature completion percentages. The complete matrix retains 72 traced behavioral groups, 292 plugin declarations, 55 channel manifest identities, 29 platform registration sites, 90 model-provider identities, 51 production Python tool registration calls, 55 toolset members, 339 skill paths, 1855 documentation surfaces, 827 external catalog references and 7 execution backend records. Some rows are fixtures, vendor packages, alternative transports, historical docs or repeated descriptions and need explicit applicability decisions. No external catalog plugin is declared implemented from a URL alone.

Measured baseline: fresh-main 242 passed/1 skipped; two native inference probes produced matching direct/routed answers. Those results protect existing behavior, not feature parity. Upstream runtime tests and unified acceptance are not run. The selected local adapter's previously failed numerical quality/retention gates remain failed; its existing owner exception is not a new success or promotion.

## Open blockers and decisions

- Expanded audit approval is required before Zenith implementation under the latest user instruction.
- PR18/19 remain open and overlapping; select/reconcile a reviewed base, preserving both branches and all model/data artifacts.
- Reference runtimes need supported Node/Python environments, dependency installation and their own bounded execution policies before equivalent live comparisons.
- Actual model tool-use and planning capability must be measured with unchanged selected Zenith; an integration cannot guarantee a small model's task quality.
- Messaging/provider services need legitimate account access and per-transport testing; API keys do not grant universal model access.
- External catalog packages need source/license review; platform apps require build/signing/devices and OS permissions.
- Sandbox/browser/remote/GPU/media/concurrency/learning acceptance remains unmeasured. These are missing engineering work, not documentation-complete features.
- A source inventory can be broad without proving every dynamic branch. Regex/AST metadata, manifests and doc headings are coverage aids; runtime equivalence and security require the planned executable tests. Later reference commits require a new delta audit.

Each implementation PR must move only its tested rows forward and retain blocked/unimplemented rows. Final acceptance requires all applicable contracts verified or explicit approved exclusions, with real environment and test evidence. No claim that Zenith became Hermes, OpenClaw, a proprietary frontier model or a newly trained foundation model is warranted.
