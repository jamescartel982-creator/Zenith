# Reproducible evaluation and baseline

## Fresh observed results

Source baseline: `fcec8993b068cc72f2ca918a8ef5680dbc9b2255`. This is the existing
system before any proposed upgrade; there is no new candidate or post-upgrade
accuracy result in this audit.

| Check | Actual result | Scope |
| --- | --- | --- |
| Root suite | 363 run, 362 passed, one platform skip, 45.041 s | Application/unit/integration fixtures; not 363 real model tasks |
| Inference service | 13 passed, 0.367 s | Protocol/admission fixtures; actual model measured separately |
| Runtime bridge | 33 passed, 4.013 s | Native client/auth/session/cancellation fixtures |
| Trading service | Seven passed, 0.500 s | Service/risk/report contracts; not fresh native financial graph execution |
| Deployment services | 12 passed, 0.163 s | Unit rendering, permissions, rollback and actual systemd parser where available; no permanent services started |
| Local HTTP smoke | Passed | Actual loopback startup/security/body/UI behavior; fixture response is not a neural benchmark |
| Package compatibility | Passed, 81 distributions | All installed requirements compatible |
| Source manifest | 714 files verified | Consistency, not a signature or supply-chain proof |
| Real trained checkpoint | Strict load/inference passed; identity and parameters unchanged | Existing base + learned LoRA, original saved tokenizer |
| GPU use/VRAM | Unavailable | No GPU in this two-CPU, 8-GiB executor |

The real-model baseline uses deterministic CPU generation, three configured CPU
threads, 64 output-token cap and 2,048 input budget. Strict model loading took
15.876 s, including integrity work. Peak process RSS was 3,527,360 KiB
(3,444.7 MiB), including load/finite-weight validation/inference; it is not
steady-state serving RAM or system-wide peak. Actual model details and hashes are
in [current-model-baseline.json](current-model-baseline.json).

| Existing authored diagnostic path | Raw score | Median latency | Interpretation |
| --- | --- | --- | --- |
| Application suite, all 14 cases | 11/14 under v1 scorer | 5.217 ms | Nine cases use deterministic/guard paths; this median is **not model latency**. |
| Model-generated subset, five cases | 2/5 under v1 scorer | 3,184.749 ms | Small public development subset; scorer false negatives require review. |
| Model-generated first visible text | Not an accuracy score | 1,676.960 ms | First visible text, not necessarily first internal generated token. |
| Native reasoning probes | 2/3 exact-string matches | Per-case values in JSON | Arithmetic correct; JSON whitespace fails strict literal scoring. |
| Existing bounded reasoning engine | 2/3 exact-string matches | 6.304 / 14.499 / 5.952 s | Same exact-match outcomes, additional review/call cost; not an improvement. |

The two arithmetic reasoning probes passed on both paths. The JSON probe returned
`{"ok": true}` instead of exact `{"ok":true}` on both paths: semantically equal JSON,
but a legitimate exact-byte mismatch if byte formatting is the declared task.
Do not conflate that distinction with inability to produce JSON or solve reasoning.

Manual scorer review, retained separately from raw scores:

- `science-unit` answered `Newtons`; v1's word-boundary match for `newton` rejects
  the plural although it identifies the correct SI unit. A new unit-aware scorer
  needs positive and negative controls, not an unreviewed substring relaxation.
- `finance-diversification` paraphrased risk distribution across assets and added
  Chinese text. Lexical matching missed required terms; quality/format needs human
  review rather than automatic labeling as wholly wrong or wholly correct.
- `unknown-personal` gave an indirect statement about not determining a serial
  number, rather than a clear evidence-qualified abstention. The current abstention
  regex missed it. This is a communication/evidence issue, not demonstrated
  fabrication of an actual serial number.

No corrected universal accuracy percentage is asserted from this review. Version
new graders/suites, retain v1 results, and distinguish exact formatting, semantic
correctness, helpfulness and unsupported detail. Do not calibrate on mislabeled or
public final-test examples or train solely to exploit grader quirks.

## Existing speed evidence, separate from this audit

[Scoped-KV reports](https://github.com/n8storm/Zenith/tree/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/docs/benchmarks/scoped-kv)
record real earlier paired inference. The final run measured 9.418 s to 0.786 s
(11.98x) for a warmed matching long-context continuation, with 27 versus 1,220
actual processed forward positions. Other successful trials ranged 8.97–13.73x.
All paired answers matched; fresh requests varied in both directions. It is
not a 5,000x overall speedup, GPU result, decode-throughput gain or four-runtime
end-to-end speed claim. Latest-head real-model CI run 40764796439 passed on
Linux, Windows and macOS ARM64 at d46aa5b before its merge into this baseline.

## Reproduce the current baseline

Use the existing selected, locally cached, trained adapter and its verified
inference identity. Do not materialize replacement weights or activate a new
checkpoint merely to run this baseline. `baseline_probe.py` is an audit driver,
not a production component. Its RSS measurement uses Linux resource semantics.

```bash
uv sync --project integrations/inference_service --frozen --extra local --extra test
uv run --project integrations/inference_service --frozen --extra local --extra test python docs/system-upgrade-audit-20261029/baseline_probe.py --identity /path/to/existing/identity.json --output /path/to/new-baseline.json
```

When using the standalone audit folder, provide the repository on PYTHONPATH or
use the installed frozen environment, and run from the pinned repository root.
The driver verifies the exact selected model/revision/adapter identity, strictly
loads learned finite weights/tokenizer, runs the frozen existing application and
reasoning fixtures, records actual usage/resources, and checks profile/artifact/
loaded-parameter fingerprints afterward. It refuses output overwrite. This is
CPU-only; it neither changes a profile nor trains/promotes a model. Raw test logs
are retained in the audit delivery folder; test-owned data was temporary.

Root suite: `python -m unittest discover -s tests -v`. Independent service suites:
use their frozen environments and unittest discovery paths already in their CI
workflows. `python -m scripts.smoke_server` checks actual local HTTP. Avoid running
CPU-heavy tests concurrently with latency benchmarks. Root test extra does not
install every optional integration SDK; use the corresponding isolated environment.

## Frozen future evaluation plan

Each experiment manifest must include Git/model/tokenizer/adapter identities,
data/source licenses and revision hashes, scorer version/hash, split IDs,
prompt/template hashes, seed/temperature, output/context/call budgets, dependency
locks, hardware/runtime versions, cache/load state, resource bounds and raw
per-case outcomes. Baseline/candidate workloads must be identical. Separate
development, calibration validation and held-out final test; never mix final-test
examples or proprietary provider outputs into training without rights.

| Category | Proposed frozen acceptance | Required evidence / unavailable handling |
| --- | --- | --- |
| Reasoning | Reviewed multi-step/math/constraint tasks; licensed GSM8K subset where appropriate | Exact/semantic intent separated; correctness, verification failures, slices and calibration; not just model agreement |
| Coding | Real repo bug fixtures, licensed HumanEval+ and selected SWE-bench tasks | Hidden tests in isolated toolchains; patches, affected files, logs, no test-gate editing |
| Agents | Deterministic multi-step tools/DAGs, cancellation, delegation and unknown-effect cases | Real controller/backend execution, completion checks, bounded calls, receipts, restart behavior |
| Memory/graph | Owned projects/documents with frozen relevant IDs, contradictions and deletion cases | Recall@k/MRR, supported answers, cross-owner leakage=0, retention/deletion and source provenance |
| Research | Retrieved source snapshots and labeled claim-support examples | Citation precision, support/contradiction assessment; no fabricated or unavailable source access |
| Cybersecurity | Licensed benign/security lab fixtures and labeled logs/dependencies | Detection/false positives, correct remediation, scope/approval enforcement; no unauthorized external tests |
| Vision/OCR | Approved frozen images/screenshots/charts/documents | Actual configured model/OCR, extraction/VQA accuracy and unsupported cases; no metadata-only completion |
| Speech/voice | Licensed/consented clips, turn/interrupt fixtures | WER, transcription/turn latency, playback interruption, no cross-session audio |
| Video/documents | Small representative files with labeled spans/events | Actual extraction, bounded decoding, citations/time ranges, malicious-input tests |
| Infrastructure | Identical warm/cold prompts and concurrent sessions | TTFT/visible text distinguished, tokenizer output TPS, latency, peak RSS/VRAM, GPU utilization, errors and known cost/success |
| Evolution | Seeded proposal, experiment, regression, approval and rollback fixtures | Reproducible artifacts, deliberate failures rejected, no self-approval, actual canary rollback within approved policy |

Run enough repetitions to characterize variance; record p50/p95 and sample counts,
paired differences and uncertainty where justified. Pre-register slice minima and
quality/security/resource thresholds before optimization. Unknown required metrics
block a gate. A small arithmetic smoke is not a comprehensive intelligence score.

Unit fixtures, protocol integrations, real model tests, real upstream runtime tests,
platform/browser/desktop tests and production soak are separate evidence levels.
GSM8K/HumanEval+/SWE-bench, GPU, multimodal, full upstream parity and permanent-host
soak were **not run in this audit**. Their future rows remain unverified/blocked
until the actual configured backend and environment pass.
