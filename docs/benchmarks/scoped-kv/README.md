# Scoped attention reuse

This optimization preserves the selected Zenith checkpoint, adapter, tokenizer,
precision and generation settings. It reuses matching attention state for the
same authenticated account and conversation. Every response still executes the
model; responses are not memoized. The Hugging Face provider also retains one
generation worker and avoids repeating the final chat-template tokenization.

## Measured results

The unchanged provider at `7b6bbff7a559ce29c2e3a8b2cc641b926463c1ce`
and the candidate ran alternately on the **same loaded trained model**, three
samples per case and implementation. Temperature 0, output limit 16, CPU float32,
three configured CPU threads, SDPA, two-CPU container quota, no GPU. Model loading
and warm-up are excluded. This is a synthetic project-context workload, not a
general intelligence or four-runtime end-to-end benchmark.

| Case | Baseline median | Candidate median | Baseline / candidate |
| --- | ---: | ---: | ---: |
| Fresh short arithmetic | 1.653 s | 1.757 s | 0.94× |
| Fresh project context | 9.350 s | 8.528 s | 1.10× |
| Follow-up on that context | 9.418 s | 0.786 s | **11.98×** |

Full timings, first visible text, output-token throughput, source/configuration
identities and actual forward-work counters are in [paired-final.json](paired-final.json).
Earlier [paired-first.json](paired-first.json), [paired-pre-review.json](paired-pre-review.json)
and [paired-review.json](paired-review.json) preserve all successful local paired
trials, including the builds before review fixes. Follow-up gains ranged from
8.97× to 13.73×. Fresh-context differences ranged from about 16% slower to 10%
faster; short requests also varied in both directions. Host noise and the small
sample make fresh-request speedup claims unreliable. These runs do not demonstrate a
5,000× overall improvement, faster decode throughput, or a GPU speedup.

In every run all nine paired responses matched exactly (`4`, `READY`, `56`).
Each continuation kept 1,218 logical input tokens but reused 1,193 token positions;
only 25 prompt positions needed computation. Including decode, a forward hook
counted **27 versus 1,220** processed positions, with one real generation per reply.
Logical token reporting is unchanged; reused/computed counters report model work,
not external-provider billing discounts.

Final real-model checks verified identical prompts from another owner, another
conversation, and an anonymous caller reused **zero** tokens. The original
owner's follow-up reused 1,193. Editing the prompt matched fresh uncached inference.
Cancellation triggered during a real forward pass yielded no partial reply and
removed the affected state. Checkpoint/tokenizer identity, saved profile bytes
and every loaded parameter stayed unchanged:

- Preserved identity SHA-256: `182559bbb77dad2ac9f53be2252ef0fa8a3698851d8d47708d5264701170e13b`.
- Runtime parameter SHA-256: `9abde1fc20e926e8e8ba62660bf14155c3cb6c0e67bb794164a1a758278f6b60`.

An initial exploratory implementation missed two of three reuse opportunities:
stream completion cancelled the worker before cache admission. The fix joins
successful work before signalling completion. Deterministic tests exercise normal
completion, early stream closure, cancellation while joining, and errors after
text ends. Failed exploratory timings are not counted as successful improvements.
Review also identified a thread-owned streaming lock that could fail when HTTP
worker threads changed. A transferable lock and cross-thread resume/close tests
fix that lifecycle. The benchmark now binds the selected model, revision, cached
snapshot and loaded tokenizer to the verified identity before measuring.

## Scope, memory and rollback

Reuse currently applies only to the root application's authenticated
`HuggingFaceProvider` streaming conversations with full-attention Qwen2 and a
compatible Transformers `DynamicCache`. The scope comes from account/conversation
IDs supplied by the application, never prompt text. Exact token IDs, including
roles and tokenizer delimiters, must match. Changed context crops state to the
shared prefix; at least one input token is always computed. Unsupported models
and anonymous calls use ordinary generation.

The default **64 MiB per-provider** cache retains at most eight conversations for
90 seconds of idle time. Expired entries are removed on the next cache operation;
there is no background cleanup timer. Physical tensor backing storage, including
storage retained after cropping, is charged to the budget. One generation runs
at a time; state is removed before mutation and admitted again only on success.
State exists only in process/device memory and is cleared on close/restart. It is separate
from persistent account memory and never written to disk.

Set `ZENITH_KV_CACHE_MB=0` to disable attention reuse (accepted range 0–512).
Restart after changing it. No data migration, adapter change or checkpoint
rollback is needed. Worker/tokenization improvements remain with caching disabled.

Ensemble children, standalone native inference, Hermes, OpenClaw, TradingAgents,
Ollama and external API providers do not gain cross-request caching here. Their
routes, credentials and model identities remain unchanged. The existing ensemble
default is preserved; select your existing Hugging Face model explicitly to use
this path. Do not share an owner scope among unrelated callers or expose
`stream_scoped` directly as an unauthenticated API.

## Reproduce

Use the existing selected, locally cached trained checkpoint and a separately
captured inference identity. Never select random weights or replace your current
adapter for this benchmark. The optional frozen inference environment supplies
the identity verifier and actual inference dependencies:

```bash
uv sync --project integrations/inference_service --frozen --extra local --extra test
uv run --project integrations/inference_service --frozen --extra local --extra test python -m scripts.inference_speed_benchmark --identity /path/to/existing/identity.json --output /path/to/new-report.json --samples 3 --scoped-cache --baseline-ref 7b6bbff7a559ce29c2e3a8b2cc641b926463c1ce
uv run --project integrations/inference_service --frozen --extra local --extra test python -m scripts.inference_speed_acceptance /path/to/new-report.json
```

The full baseline commit must exist locally (`git fetch` if necessary). Baseline
provider source is loaded from that explicitly selected local ancestor and shares
the already loaded model/tokenizer, not attention state. Source hashes are checked
at the end; do not edit runtime files while measuring. Output overwrite and
protected artifact paths are rejected. Reports include the original source commit
plus hashes identifying the exact uncommitted candidate source measured.

The `Scoped inference performance` workflow reconstructs the same byte-verified
trained adapter in an isolated directory and runs real-model comparisons on Linux,
Windows and macOS ARM64. It gates correctness, preservation, work reduction,
isolation and cancellation. Virtualized latency is reported without an arbitrary
universal speed threshold. No GPU, remote service or paid API is required.

Local validation: 363 root tests passed (one platform-specific skip), including
17 focused cache/worker/scope/identity regressions; 13 inference-service and 33 bridge
tests passed. These deterministic service tests supplement the real preserved
model measurements above; they do not establish four-runtime performance gains.
