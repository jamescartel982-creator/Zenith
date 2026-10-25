# Model registry and orchestration (Phases 1–2)

These optional layers extend the existing Zenith providers. They do not change model weights, tokenizer, adapter selection, saved profiles, SQLite schema or installation commands. The existing `AI_PROVIDER` continues to work. The audit, exact artifact hashes and baseline evidence are in [platform audit](platform-audit/README.md).

## Use native Zenith

After the ordinary installation, use the existing launcher or installed `zenith` command:

```bash
zenith model-registry list
zenith route "Explain how binary search works."
zenith route "Check the assumptions in this argument." --mode deep --effort deep
zenith route "Explain this Python function." --mode coding
zenith route "Summarize relevant locally imported documents." --mode research
zenith route "Explain transformer attention." --mode local-only
```

From the checkout, `python -m agent` can replace `zenith` (use the installer's `.venv` interpreter or launcher). `route` defaults to the existing Hugging Face model, pinned revision and selected adapter. `ZENITH_NATIVE_PROVIDER=ollama`, `localserver`, or `tiny` explicitly selects an existing alternate local runtime. Hugging Face inference here requires cached files and uses `local_files_only=True`; run the existing `zenith models download` using the original provider configuration if necessary. Native/local-only execution does not discover external accounts, send paid requests or download models. Loopback endpoints must be local; their operator must also configure the server for offline inference if required.

For ongoing terminal/browser chat, explicitly set `AI_PROVIDER=orchestrated`. The default `ZENITH_ORCHESTRATION_MODE=native`, `ZENITH_ALLOW_EXTERNAL=false` preserves local-only model selection. The old `fast`/`thorough` response-length controls remain independent of orchestration mode. Do not replace your saved adapter or deployment receipt. No automatic configuration migration occurs.

## Optional account providers

Credentials come from `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` in the process environment. Zenith does not create keys, put them in prompts, write them to configuration, log them or require them for local inference. No keys were available for live provider validation in this delivery.

```bash
zenith model-registry discover --provider openai
zenith model-registry discover --provider anthropic
zenith model-registry discover --provider ollama
zenith model-registry discover --provider localserver
zenith model-registry discover --provider huggingface --query "Qwen"
```

Discovery does not run inference. Anthropic pagination is bounded and follows the account's cursor; exact IDs, line/family, lifecycle, context/output limits and supported reasoning effort come from its Models API when present. OpenAI's Models API gives basic account-visible IDs and shutdown dates; it does not establish endpoint compatibility, context, price or every supported modality. Missing metadata stays unknown. A listing is not a guarantee that inference will succeed. A failed refresh makes stale non-native entries unavailable. A model denied at inference is not retried as an authorization workaround.

GPT, Codex, Claude, Mythos, Fable, Opus, Sonnet and Haiku are searchable family references. Historical IDs are explicitly unavailable reference entries until actually returned for the account and configured. No made-up IDs, wildcard access, preview access programs or bypasses are implemented. Restricted IDs not returned by the account remain unavailable. Public Hugging Face/GitHub discovery retains its existing metadata-only behavior and license/compatibility review requirements. An HF checkpoint can use the existing local provider with its exact base/revision/adapter, or a trusted plugin binding; metadata search never installs or executes repository code.

Set `ZENITH_EXTERNAL_MODELS` to a JSON array of explicitly chosen IDs, using actual IDs from your own account discovery. The following is a configuration shape, **not an assertion that these placeholder IDs exist or are accessible**:

```json
[
  {
    "provider": "openai",
    "model_id": "ACCOUNT_DISCOVERED_EXACT_RESPONSES_MODEL_ID",
    "api": "responses",
    "context_window": 32768,
    "max_output_tokens": 1024,
    "tags": ["coding"]
  },
  {
    "provider": "anthropic",
    "model_id": "ACCOUNT_DISCOVERED_EXACT_MESSAGES_MODEL_ID"
  }
]
```

Replace placeholder limits and tags with independently verified model facts or omit unknown values. Pricing, if supplied, must include `input_usd_per_million`, `output_usd_per_million`, and an HTTPS `source`; no built-in price or leaderboard is invented. Exact snapshot IDs are required: current adapters reject responses resolving to a different model ID instead of silently attributing an alias response to another model. Unknown OpenAI text/Responses compatibility must be explicitly declared with `api: responses`. Declaring an ID alone does not make it available; successful account discovery is also required. Native identity cannot be overridden through this array.

Sending conversation content requires a second explicit opt-in:

```bash
zenith route "Compare approaches to this problem." --mode collaborative --allow-external
zenith route "Explain this code." --mode fast --allow-external
```

The full context can include conversation history, selected personal notes and imported document excerpts. Enable external calls only when that context may leave the local machine. For ongoing chat use `ZENITH_ALLOW_EXTERNAL=true` and a non-native mode deliberately. `HF_HUB_OFFLINE=1` also disables the wrapper's external calls. Native/local-only modes override the external flag. Discovery requests require their explicit CLI action even in otherwise local workflows.

## Routing and failure behavior

| Mode | Implemented behavior |
| --- | --- |
| Native | Existing selected Zenith runtime only. No external fallback. |
| Fast | Prefer measured in-process latency after eligibility checks; unknown latency defaults to native. No claim of a global fastest model. |
| Deep | Answer plus a separate model-review call within the total call/deadline budget. |
| Coding | Prefer explicitly configured coding tags and measured quality when supplied; otherwise local Zenith. Does not execute code. |
| Research | Reuse existing SQLite document retrieval and untrusted-source attribution, then review support. Multi-query web research belongs to Phase 7. |
| Collaborative | At most two independent successful model drafts and a synthesis call. If another model/synthesis is unavailable, label the returned draft as degraded. No weight merging. |
| Local only | Local runtime bindings only, no account discovery or external calls. |
| Security research | Native model only after the trusted Python caller supplies live owner/MFA execution controls, an explicit capability, literal target and approved scope. Grants are rechecked after inference. Ordinary chat cannot authorize this mode. No new execution tool is added. |

`RoutingRequest` supports context requirements, modality/tool filters, provider-cost estimates, output tokens, total model-call limits, zero–two retry attempts, and cancellation. Text-only execution rejects tool or multimodal requests even when the provider metadata advertises them. Actual tool execution must still use `ExecutionControls.execute`; the orchestrator cannot grant permissions or run shell commands. Security secrets are kept outside model messages. Existing server-side MFA, expiration, revocation, audit and emergency stop remain authoritative.

A provider-cost cap excludes models with unknown pricing and reserves estimated cost even when a request fails. This is a conservative provider estimate, not a billing guarantee or measurement of local electricity/compute. All stages, including review/synthesis, share the call and estimated-cost budgets. Retries apply only to transient transport/upstream failures; access-denied requests are not retried. Two failures open an in-process 30-second circuit breaker; no detached inference workers continue after a completed cancellation.

Deadlines are **cooperative**: checks occur before/after requests, between HTTP body reads and native generation steps. Connection/read idle timeouts bound external I/O; existing local transports keep their established blocking read bounds. Model loading, kernels and a blocked local HTTP read can delay cancellation. This delivery does not claim preemptible GPU kernels or strict wall-clock deadlines. Hard worker isolation belongs to later execution/infrastructure work.

The existing native generator supports token streaming; this orchestration version buffers the complete answer, including collaboration/review. Its first visible text time includes those stages and must not be called model time-to-first-token. It does not advertise a speed improvement.

Each persisted response names its producing model and carries a draft/synthesis/review trace. Traces record usage when reported, latency, fallback reasons and uncalibrated review status; they do not contain hidden provider reasoning. A review is a fallible model opinion, not objective factual verification. Invalid JSON reviews remain `unverified`. A failed review never turns into a successful numerical model-promotion gate.

## Training provenance and plugins

No training is performed in Phases 1–2. `Store.approved_examples()` excludes any conversation that used external model output, including later locally generated turns with that output in their context. Clicking “approve” does not confer provider-output training rights. Human-reviewed external corrections need a future explicit provenance/rights workflow; this delivery deliberately has no bypass. Manually copied text still requires the dataset ingestion process's existing licensing/provenance review.

`ProviderAdapter` is a trusted Python protocol exposing `name`, `discover(context)` and `generate(record, messages, context)`. Register adapters and records on `ModelRegistry` from application code. A local adapter binding calls the existing provider factory; optional capabilities do not modify tokenizer embeddings. No arbitrary entrypoint, plugin code or tool description is loaded from a prompt, catalog entry, downloaded repository or provider response. Routing observations are local to the process and accept latency or separately measured quality; no ranking claims are inferred from model names.

## Validation, migration and rollback

See [results](platform-audit/results.md) for actual measured tests and live native inference. The remote adapter fixtures use real local HTTP sockets and validate protocol/error behavior; they are not live proprietary-model benchmarks. No GSM8K, HumanEval+, SWE-bench, multimodal or paid-model results are claimed for this phase. The model compatibility report is the matrix above plus the account/transport limitations described here. Original frozen quality/retention failures remain unchanged.

No database columns, profile edits, model files, identity changes or model deployment are required. Disable orchestration by restoring your previous `AI_PROVIDER` (usually `huggingface`), restart Zenith, or revert this feature's application commits. Your original model files and deployment rollback receipts remain intact. The primary Windows/Linux Git-clone and `install.py --mode local` flow is unchanged.

Official protocol references checked 2026-10-25:

- [OpenAI Models](https://developers.openai.com/api/reference/resources/models/methods/list)
- [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Anthropic Models](https://platform.claude.com/docs/en/api/models/list)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)

Phases 3–15 remain planned; this feature is not a claim that Zenith is GPT, Claude, Mythos, or a newly trained frontier foundation model.

### Phase 1/2 review hardening

Routing privacy flags require actual booleans: strings such as `"false"` are rejected rather than interpreted as consent. Retry counts require integers; budgets, prices and latency observations reject non-finite or invalid values. Discovery validates capability/availability metadata before it becomes routable; a malformed provider listing fails closed and native fallback remains available. Every draft/review/synthesis stage rechecks current availability, so an earlier access denial cannot be retried merely because a long local call outlasted the circuit-breaker timer. A review reporting issues remains a concern even if it also reports `supported: true`.
