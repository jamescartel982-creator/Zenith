# Measured platform pilot results

Measured on 2026-10-25 UTC. These results cover the foundation/supervised pilot,
not completion of the OpenClaw roadmap. No model training or promotion occurred.

## Regression and real execution

| Check | Actual result |
| --- | --- |
| Fresh unchanged-main suite | 243 run, 242 passed, one skipped; 39.139 s |
| Foundation suite | 261 run, 260 passed, one skipped; 42.343 s |
| Final suite | 275 run, 274 passed, one skipped; 56.966 s |
| Newly added platform tests | 32 tests passed within the final suite |
| Dependency consistency | `pip check`: No broken requirements found |
| Regular wheel | Built/installed into a separate target and imported outside checkout; 131 hashed installed files verified; supervised task completed |
| Real Uvicorn / loopback HTTP | Authenticated queued arithmetic completed, scoped SSE replay succeeded, bearer alone could not supply account/owner authority; tools stayed disabled |
| Real owned diagnostic transport | Unit/integration fixture connected to its explicitly scoped loopback socket once, only after exact human approval |
| Model/profile protection | Original selected adapter file inventory and saved profile unchanged; no checkpoint writes or data reset |

Raw [test output](tests.log), [HTTP smoke](http-smoke.json), [package smoke](package-smoke.json) and
[native inference evidence](native-smoke.json) accompany this report. Tests use
owned temporary state. Some provider tests use test doubles, explicitly labeled in
their modules; those do not substitute for the native inference run below.

## Existing trained checkpoint, paired CPU smoke

- Base: `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`.
- Selected LoRA SHA-256: `7e0701900b40109ee81b3dc097985cda360409006c8b717bda51830f3b6ed85d`.
- Tested runtime commit: `c5ee83410045f7adce1cdf883928ac96b848fcf9`; exact Python-source hash is in the raw evidence.
- Device: cpu; 2 CPU threads; temperature zero; 32 output-token budget.
- Cold load: 9.856 seconds. Temporary data/accounts; offline cached artifacts; zero external model calls.
- Three alternating-order warm pairs using the same one-sentence rain prompt and unchanged model/tokenizer.

| Pair | Legacy API end-to-end ms | Queued API end-to-end ms | Exact output parity |
| --- | --- | --- | --- |
| 1 | 6107.202 | 9855.643 | true |
| 2 | 6423.591 | 8004.760 | true |
| 3 | 6595.394 | 13175.544 | true |

Median observed latency was **6423.591 ms legacy**
and **9855.643 ms queued**. The queued path was
slower in this sample. No speed improvement is claimed. Queued timing includes
admission and 20 ms completion polling; model-reported timings, first-text latency,
outputs and per-call usage remain in the raw records. This small shared-host
sample does not isolate every overhead or establish a general latency distribution.

All six generations used 204 input + 16 output tokens (220 total), one model call
per answer. Outputs matched, but output parity is not a scientific correctness
benchmark. The short answer omits important details of condensation; no new domain
competence, general accuracy, frontier performance or token savings is inferred.

GPU utilization, peak RAM/VRAM, concurrent throughput, broad task success,
statistical noninferiority, sandbox escape resistance, channel E2E and proprietary
provider costs were **not measured**. No fictional zero values or completed gates
are supplied for these categories. The three prompts/pairs are authored smoke
fixtures, not GSM8K/HumanEval/SWE-bench or a sealed generalization evaluation.

## Acceptance boundary

The tested foundation and supervised workflows are available for opt-in review.
This is not approval for production activation or external exposure. In
particular, the latency result leaves performance optimization unfinished.
Autonomous tool generation, general code sandboxing, plugins, multi-agent,
private semantic/project retrieval, channels, browser/computer automation and new
dashboard controls remain unimplemented/unavailable. Their broader security and
benchmark gates have not passed merely because this suite passed.

The existing experimental trained candidate's failed numeric quality/retention
gates remain recorded; this work does not relabel, register, retrain or promote it.
See [boundaries](architecture.md) and [rollback](operations.md).
