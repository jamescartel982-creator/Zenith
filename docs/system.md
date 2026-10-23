# Zenith's five components

Open **System** in the chat header to inspect the current configuration and your local performance metrics. `zenith system` provides the component view in a terminal; `zenith system --metrics` reads server aggregates as the local OS operator.

| Component | Working implementation |
| --- | --- |
| AI model | Hugging Face, Ollama, a key-free loopback model server, the bounded configured team, or Zenith's experimental scratch transformer. Models load lazily; catalog entries alone do not run. |
| Harness | Responsive browser chat, streamed HTTP API, terminal streaming, safe Markdown, feedback, reply-length controls, and a Stop button. |
| Context / memory | Recent complete conversation pairs, explicit account-private notes, and bounded source-linked excerpts from the shared local index. The model receives a selected context; stored history is separate. |
| Infrastructure & data pipeline | CPU/CUDA/MPS inference through PyTorch when available; compatible local endpoints manage their own hardware. SQLite WAL stores local state, FTS5 provides lexical retrieval, source snapshots and manifests version data, grouped splits isolate train/validation/test, and candidate training never promotes itself. |
| Governance & monitoring | Account and owner authorization, secret rejection before model/storage, explicit training approvals, conservative abstention, local human review, versioned regression evaluation, private performance aggregates, and a bounded scheduled diagnostic watch. |

The implementation uses SQLite FTS5, **not a vector database**. It does not provision GPUs/TPUs or microservices simply by listing them. A GPU is used only if supported, installed, and selected; local-server hardware belongs to that runtime. The System view reflects configured/loaded state without probing remote hardware or exposing secret files, local endpoints, or memory contents.

## Shorter replies and less token work

**Fast** still calls one routed contributor; **Thorough** performs the configured review/synthesis. The new **Length** control is independent:

- **Auto**, the default: simple fast questions receive a compact prompt, at most 96 new tokens, the last four conversation turns, and at most two shorter retrieved excerpts. Code, long requests, explicitly detailed work, and thorough mode retain the full configured budget.
- **Brief** always applies the smaller budget and bounded recent context.
- **Full** retains `MAX_NEW_TOKENS` (default 256), up to 12 history turns, and the configured retrieval limit.

Every budget remains capped by the operator's `MAX_NEW_TOKENS`. These are maximums, not actual usage. Output can be shorter. Your earlier turns remain saved; a brief request simply sends fewer to the model. Use Full or explicitly saved memory when older details matter. Code/detail detection is a heuristic: choose Full yourself for an incorrectly shortened request.

```text
ZENITH_REPLY_STYLE=auto
ZENITH_FAST_MAX_NEW_TOKENS=96
ZENITH_FAST_HISTORY_TURNS=4
```

The compact prompt removes repetition while retaining uncertainty, memory, evidence, and permission boundaries. Hugging Face uses the model's generation KV cache. Changing a request's budget reuses cached weights; it does not create a second model. No cross-user answer cache or automatically generated memory summary is introduced.

```text
zenith chat --reply-style brief --stats
zenith chat --reply-style full
zenith serve --warmup
```

`--warmup` loads and exercises the first configured contributor before accepting requests. The initial download/load still takes time; it moves that wait to startup. It does not warm every catalog model. Without this flag the server stays quick to start and loads on demand. Large reasoning models may need a larger output budget and substantial hardware; a tiny token cap can prevent them producing a useful final answer.

## Usage and cancellation

Completed replies show reported input/output tokens and first visible text latency when available; those records survive reload. Hugging Face counts actual model tokens, including generated EOS where present. Ollama/local servers supply counts through their protocol. Missing counts stay unknown. Tiny uses UTF-8 byte tokens, which are not directly comparable with other tokenizers. Team totals sum available per-call reports; a missing call count makes token totals unknown rather than silently undercounting.

`finish_reason=length` exposes when a reply reaches its budget. The browser offers **continue with Full**, which prepares a continuation request for you to send. Brief answers are not guaranteed complete merely because the model stopped naturally.

**Stop** aborts browser reception; the server cooperatively closes the stream and joins Hugging Face generation before reusing the model. Incomplete replies are discarded. A reply already completed before cancellation remains in history. A current native forward pass or pending HTTP read can delay server cleanup; another request may briefly receive HTTP 429. Terminal replies stream too, and Ctrl+C closes their stream before exiting.

## Private performance monitoring and regression watch

Generation metadata includes status, configuration hash, request mode/style, timing, reported token counts, and whether the cap was reached. The monitoring table stores no prompts, answers, memory text, owner codes, or tool inputs. Records are bounded to the latest 1,000 started requests globally, up to 30 days, with cleanup on reads/writes. Deleting a conversation deletes its linked performance records. Existing conversation storage remains separate and still contains chat text.

`/api/metrics` requires sign-in and returns **that account's aggregates**. `/api/admin/metrics` additionally requires current owner elevation. The local terminal operator can inspect all aggregates with `zenith system --metrics`. Browser account changes clear displayed private aggregates. These metrics cover generations that started; they are not a complete HTTP/security access log.

Model-generated latency medians are kept separate from instant built-in checks. Like-configured cohorts include mode, reply style, model/revision, context/output limits, temperature, device policy, thread count, and team configuration. After at least 40 observations, a recent 20-request median over 1.5× the preceding 20 creates a review signal. Output length, workload, cold loads, and system load can explain the change. It is **not a factual-accuracy drift detector**. Pin models/adapters and regenerate calibration when weights or serving runtimes change; configuration hashes do not fingerprint mutable remote weights.

The **Scheduled diagnostic regression watch** GitHub workflow runs on relevant pull requests, `main` updates, manual dispatch, and weekly. It evaluates the pinned small default model against a frozen public development baseline, fails on task-slice accuracy regressions, and retains its report for 30 days. It uses isolated CI data, a 15-minute budget, no paid model API keys, and no private conversations. Scheduled Actions can be delayed or disabled by GitHub repository policy. It never changes source, weights, data approvals, or active adapters. Maintain a separate representative, labeled evaluation set for production decisions; the public 14-case diagnostic is too small to certify broad robustness or prevent every drift.
