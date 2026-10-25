# Baseline evidence and proposed benchmark plan

**Audit date:** 2026-10-25 UTC. **OpenClaw:** `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. **Zenith main:** `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. This is an audit/design deliverable; no Zenith implementation changes are authorized in this delivery.

**Evidence labels:** S = source-verified at the pinned commit; M = measured here; D = upstream documentation/policy claim; P = proposed design; H = hypothesis requiring implementation or experiment. Source inspection does not establish successful live execution.

## Actual measurements in this audit (M)

| Observation | Result | Meaning / limit |
| --- | --- | --- |
| Fresh cloned-main regression suite | 243 tests run; 1 skipped; no failures; 34.864 s | 242 passed, 1 skipped. Existing suite only; not the proposed platform tests. |
| Existing local checkpoint verification | Loaded successfully; generated `4`; 10.319 s inspection including load/inventory | CPU, 2 Torch threads in inspection; not timed as a task benchmark. |
| Offline native harness smoke cold load | 5.754 s | Existing real HF + LoRA; 3 CPU threads for this smoke. |
| Arithmetic direct / existing native-routed | 671.744 / 565.540 ms; both `4` | One warm observation per path. |
| Geography direct / existing native-routed | 642.631 / 587.642 ms; both `Paris` | One warm observation per path. |
| Smoke answer checks | 2/2 expected answers and direct/routed matches | A compatibility probe, not general knowledge/reasoning accuracy. |
| Reported routed usage | Arithmetic 43 input + 2 output; geography 42 input + 2 output | Tokenizer-reported output includes generation terminal tokens; no direct-path usage comparison. |
| External model API calls during smoke | 0 | This smoke was offline; it does not validate remote account access. |
| OpenClaw runtime/tests | Not executed | Host Node 24.19.0 does not satisfy upstream >=24.22.1 <25 or >=26.12.1. |
| Upgraded Zenith benchmark | Not available | No integration code has been implemented or approved. |

Evidence: `../evidence/zenith-baseline-tests.log`, `zenith-model-verification.json`, `zenith-baseline-inference.json`; source of existing smoke: [scripts/smoke_orchestration.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/scripts/smoke_orchestration.py#L1). Frozen smoke-case SHA-256: `0dd80ef5a4a9ac32506b063c7195e585878d21d77663d07d4111a672b1ffa9a6`. Compare commit, base revision, tokenizer and adapter digests in [current architecture](ZENITH_CURRENT_ARCHITECTURE.md).

The lower observed routed milliseconds are **not evidence of a speed improvement**: sample count is inadequate, order/caching and timing boundaries differ, and routing buffers complete replies. TTFT, throughput, peak RAM/VRAM, GPU utilization, OpenClaw task accuracy and all new subsystem metrics remain unmeasured. Existing unit test success is not a numeric security-enforcement benchmark. No baseline-versus-upgrade chart is fabricated.

## Reproducible baseline commands

In the detached main clone, use the existing compatible Python environment, isolated temporary `ZENITH_HOME` and the approved local model cache. The exact audit invocation paths are environment-specific:

```bash
cd /workspace/openclaw-review-20261025/zenith-main
ZENITH_HOME=/workspace/openclaw-review-20261025/evidence/test-home \
  /workspace/Zenith/.venv/bin/python -m unittest discover -s tests -v
/workspace/Zenith/.venv/bin/python -m scripts.smoke_orchestration \
  --bundle research_checkpoints/recovery-v1
```

The suite exercises isolated test state. The inference smoke reads the existing selected local adapter/profile and checks unchanged hashes. Do not run unrelated installer, training, registration, activation or deployment commands as part of measurement. Preserve original checkpoints and the current failed-gate/experimental status; this audit does not promote an adapter.

## Proposed paired workloads and metrics (P)

| Category | Exact metric / denominator | Workload | Current baseline evidence | Proposed gate |
| --- | --- | --- | --- | --- |
| Task completion | Successful goal + verified final environment / all admitted tasks, with failures/timeouts separate | Owned deterministic retrieve → calculate → save-draft workflows; independent checker | Not measured | Baseline/candidate identical cases; no quality regression within reviewed noninferiority margin |
| Tool-call correctness | Exact approved tool ID/version and schema-valid normalized arguments / all proposals; invalid proposals counted | Correct, malformed, unknown tool, schema drift and error-repair cases | Not measured | Report first-attempt and eventual accuracy, extra calls and denials separately |
| Authorization | Denied forbidden attempts / all forbidden attempts; also count actual side effects | Forged owner, stale MFA, revoked grant, argument swap, emergency stop, child escalation | Not measured as benchmark | 100% forbidden attempts denied and zero unauthorized effects in frozen suite |
| Memory relevance/isolation | Recall@5 and nDCG@5 on labeled relevant chunks; unauthorized result count | Account/project contrastive documents, paraphrases, stale/deleted sources, multilingual/noisy queries | No retrieval benchmark | No cross-account results; deletion complete; semantic backend needs measured improvement over scoped FTS |
| Multi-agent coordination | Goal success, delegated-scope violations, budget compliance, orphan workers | Two independent child reads + checked synthesis; failure/cancel/restart branches | Unavailable on main | No privilege expansion or orphan effects; compare against same single-agent goal baseline |
| Latency | Cold load, queue wait, TTFT, model time, tool wait and end-to-end p50/p95 with paired intervals | Fixed prompts/workflow budgets, randomized route order, cold and warm runs separate | Two warm inference observations only | Proposed overhead budget must be agreed from larger baseline; no speed claim from two probes |
| Tokens/inference overhead | Actual input/output tokens summed over all attempts/reviews/children; overhead per completed task | Matched model/tokenizer, context and stop settings; retry accounting | Routed probes 45 and 44 total tokens; direct token counts not instrumented | Unknown usage stays unknown; report quality and tokens jointly, no fabricated savings |
| Concurrent throughput | Completed tasks/minute, error/busy rate, queue time and p95 per concurrency | 1, 2, 4, 8 sessions with per-account quotas and same HF serialization | Not measured | Bounded rejection and no cross-session state corruption; distinguish accepted from attempted throughput |
| Crash recovery/persistence | Committed tasks recovered, uncertain effects identified, duplicate accepted writes, recovery time | SIGKILL/worker loss before/after intent, acceptance and receipt; lease expiration | Not measured | Zero blindly duplicated non-idempotent writes; durable outcomes reconcile correctly |
| Prompt-injection resistance | Forbidden effect/secret leak rate per attack and benign task false-denial rate | Document/tool/skill/webpage injection across trust boundaries, synthetic secret canaries | Not measured | Zero critical forbidden effects/leaks; report finite-suite limits and benign utility |
| Sandbox resistance | Escaping fixture outcomes, forbidden network/file access, resource-limit enforcement | Owned worker attempts protected mounts, sockets, symlinks, metadata egress, process/memory exhaustion | No general code sandbox on main | All defined escapes denied; missing backend means unavailable, never safe-by-absence certification |
| Resource/cost | Peak process-tree RAM, VRAM, CPU/GPU utilization, measured provider charges or unknown | Same hardware/process/container image; optional psutil/NVML collector | CPU used; resource peaks/GPU/cost not measured | No false zeros for unavailable GPU/price; tag estimates separately |

## Workload freezing and scoring

Proposed destination `agent/evaluation/platform-v1.json` records fixture version, licenses/provenance, goal predicates, authorized actors/targets, allowed effects, initial DB/workspace hashes, prompt/input records, budgets and scoring code version. Freeze a held-out set before tuning prompts/routing. Never include private provider output or held-out benchmark examples in training. Datasets stay separate from model training and human review data.

Baseline and candidate use identical goals, selected checkpoint/tokenizer, model revision, sampling, context/output limits, owned target service images and source fixtures. For capabilities absent in baseline, score baseline as **unsupported** and compare the nearest meaningful common subset; do not represent unsupported as a successful safe refusal or calculate an invented uplift. Task fixtures use deterministic owned local services first, followed by real model inference and authorized external integrations where available.

Suggested initial experiment size is at least 30 independent repetitions per timed route and 20 seeded workflow variations per deterministic case, with more samples selected from uncertainty and failure rates. These are planned sample sizes, not completed runs. Randomize paired order; keep cold/warm phases separate, record hardware throttling and background processes. Publish median/p95 and paired bootstrap confidence intervals, sample counts, failures, outliers and unavailable checks. Use a preregistered noninferiority margin based on the larger baseline; do not invent an accuracy threshold from the two smoke questions. A zero-event result must disclose its finite denominator and cannot prove zero risk.

Use independent final-state checkers for task correctness, reference judgments for retrieval, replayed network captures for side effects and process/container-level resource collectors. Preserve raw redacted records, configuration SHA-256, exact Git commits, OS/Python/package lock versions, model/base/tokenizer/adapter hashes, container digests, provider account-visible IDs and usage-source tags. Never save raw secrets, session tokens or private document contents in shared benchmark artifacts.

## Required experiment layers

1. Unit contracts: parse/validate schemas, permission decisions, digests, bounds and transitions.
2. Integration: real SQLite migrations/ACLs/leases, actual HTTP/SSE gateway + runtime, real worker IPC, crash/recovery and explicit fail-closed paths.
3. Native inference: unchanged selected Zenith checkpoint, valid/invalid tool proposals and verified task outcomes, original chat compatibility.
4. Owned backend E2E: actual isolated browser/container/VM and real paired channel accounts with explicit scoped approval. Contract mocks alone cannot satisfy this layer. Missing accounts/backends are reported unavailable.
5. Paired performance/quality/security runs: identical workloads and independent checkers. Run a user-visible workflow through the dashboard, not only internal APIs.

The optional embeddings backend must beat scoped lexical retrieval under the agreed relevance/resource tradeoff. Optional multi-agent execution must justify extra latency/tokens against the same task's single-agent run. More calls are not inherently more intelligence. Browser/computer/channel capabilities do not ship as complete if only unit tests pass.

## Acceptance and reporting

Proposed mandatory blockers: any unauthorized side effect, credential leak, cross-account disclosure, uncontrolled host execution, checkpoint mutation, unsupported fallback bypass or silent retry of an uncertain non-idempotent action. Require no regression in current suite/installation/inference compatibility. Other quality/latency thresholds are agreed after sufficient baseline measurements. Security gates apply per enabled subsystem, not averaged into task accuracy.

Future `docs/platform/benchmark-results.md` must separate **measured**, **estimated**, **unsupported**, **not run** and **failed**. Keep raw results and failures even when a candidate is rejected. Publishing/promoting/deploying remains a separate reviewed action. This report supplies a measurement design, not evidence that the proposed implementation has passed it.
