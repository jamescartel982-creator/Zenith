# Benchmark plan

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

The [measured baseline and frozen comparison protocol](BENCHMARK_BASELINE.md) separates actual results from planned experiments. [Automated acceptance](AUTOMATED_TEST_PLAN.md) defines task, tool, memory, learning, security, persistence, multi-agent, multimodal and performance workloads. No benchmark result for a proposed subsystem exists yet.

| Requested measure | Workload / validator | Report |
| --- | --- | --- |
| Agent completion | Frozen owned repository/database/retrieval tasks; independent artifact assertions | Completed/partial/failed/blocked counts and denominator, budgets and model identities |
| Tool correctness | Schema, arguments, target and postcondition fixtures; malformed-call denial | Valid/executed/correct calls, side effects and retries |
| Authorization | Forged/stale/cross-account/changed approval and shutdown tests | Attempted denials and actual prohibited effects, with raw receipts |
| Retrieval | Frozen relevant/irrelevant multi-tenant corpus and deletion/expiry probes | Recall@k, MRR, factual consistency and isolation failures |
| Coordination | Specialists with scoped workspace dependencies and conflicting results | Validated completed graph, handoff failures, permission violations |
| Latency/tokens | Identical inference backend, fixed lengths, warm/cold and repeated complete tasks | TTFT, full median/p95, throughput, input/output/tool tokens, resource and successful-task cost |
| Concurrent throughput | Bounded sessions and actual backend queues | Successful tasks/time, latency/error distributions and resource peaks |
| Recovery | Crash at each durable state and ambiguous external write | Restored task outcomes, duplicate effects, lost events and lease fencing |
| Injection/sandbox | Untrusted document/skill/web fixtures and owned isolation probes | Observed boundary failures in finite fixtures; never universal immunity |

Pin source commits, dataset licenses/revisions, fixture/config hashes, hardware, runtimes, model/tokenizer/adapter hashes, seeds, scoped services and raw run commands before comparison. Reference runtime access and sandbox/backend availability are blockers, not zero scores. Any new pin requires delta review. The original Zenith weights and private account data remain outside benchmark mutation and public exports.
