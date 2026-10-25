# Measured baseline and proposed benchmark protocol

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Measured in this audit

Zenith fresh main `e6963d9` ran `python -m unittest discover -s tests -v` using the existing `/workspace/Zenith/.venv/bin/python`, isolated `ZENITH_HOME`, CPU-only workspace. **243 tests ran: 242 passed, 1 skipped, 33.364 seconds.** See [raw log](../evidence/zenith-main-tests.log). A skipped test is not a pass.

Native offline `python -m scripts.smoke_orchestration --bundle research_checkpoints/recovery-v1` used the current cached selected base and adapter, without activating or modifying it. [Raw output](../evidence/zenith-main-native-baseline.json): cold load **6.503 seconds**; arithmetic direct **875.938 ms** / routed **655.735 ms**, both answer 4; geography direct **887.078 ms** / routed **712.474 ms**, both answer Paris. Weight/profile unchanged flags passed. These are two correctness probes, not general intelligence, agent-completion, or throughput benchmarks. Order/warm-cache effects prevent a speedup conclusion.

## Earlier unchanged-commit pilot evidence, not rerun here

Draft PR #19 `44d55d2` previously ran 277 tests: **276 passed, 1 skipped, 40.248 seconds**. Its Windows/Linux/container checks are linked in the delivery index. Prior native direct/queued 3-pair smoke medians were **6423.591 ms / 9855.643 ms**, matching outputs and 220 output tokens each. The queue was slower on that sample; no performance improvement is claimed. This pilot handles explicit supervised plans and fixed diagnostics, not the proposed autonomous unified platform. PR18 and PR19 are unmerged.

## Not measured

OpenClaw/Hermes runtime tests, reference-equivalent task success, shell/browser isolation, new skill learning, channel delivery, multi-agent coordination, semantic retrieval relevance, prompt-injection resistance, sandbox escape resistance, concurrency, TTFT, GPU/VRAM, complete token cost and new multimodal/UI acceptance have not been run. No scores or zero-error rates are assigned to them.

## Frozen comparison protocol (proposal)

Before implementation, freeze workload IDs, fixture content/config hashes, success assertions and budgets; preserve them for baseline/reference/candidate. Run OpenClaw and Hermes in supported independent environments at the pinned commits with the **same** Zenith endpoint/model identity where technically compatible. An incompatible tool dialect is a reported blocker, not a reason to use Hermes weights. Match tool permissions, datasets, resource caps, retries, network targets and warmup. Separate reference defaults from normalized runs, because default provider/model differences confound comparisons.

For each cell record environment, dependency versions, model source, latency distribution (median/p95 and raw samples), complete/partial/failed/blocked counts with denominator, unauthorized attempts/effects, retrieval ranking, successful coordination, restart survival, token consumption and estimated versus billed cost. Use enough independent repeated tasks to report uncertainty; do not infer p95 from a two/three-pair smoke. Independent validators check the result, not the model's self-rating. Security suites report attempted cases, observed effects and tested boundaries, never a universal resistance percentage.

Store immutable experiment manifests under `benchmarks/unified/`, results under an opt-in non-private output directory and aggregate reports with raw reproducible evidence. Baseline model-only and disabled-platform overhead runs remain separate from full task-completion workloads. No benchmark may mutate the original checkpoint, production profile or user data.
