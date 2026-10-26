# Zenith inference service 0.1

An optional, independently installed, loopback-only model endpoint. It reuses
Zenith's trained checkpoint loader and saved tokenizer. It does not train,
activate, merge, rename or overwrite model artifacts. Original application routes
and native runtime configurations remain untouched.

Requires Python 3.12, the existing verified Hugging Face base and optional trained
adapter already cached locally. GGUF, arbitrary image/audio models and remote
model substitution are unsupported. A CPU environment is locked for Linux x64
and Windows x64; macOS ARM64 uses standard PyPI wheels. Intel macOS cannot run
this native Torch endpoint. The ordinary Zenith install remains independent.

Use pinned `uv 0.12.23` in a separate tools environment, then from the checkout:

```bash
uv sync --project integrations/inference_service --frozen --extra local
uv run --project integrations/inference_service --frozen --extra local zenith-inference init --directory "$HOME/.local/share/zenith-services/inference"
uv run --project integrations/inference_service --frozen --extra local zenith-inference serve --directory "$HOME/.local/share/zenith-services/inference"
```

On Windows use a private directory under your user profile instead of `$HOME`.
The operator must protect its inherited NTFS ACLs; Unix mode checks do not replace
Windows ACL administration. Do not put runtime configuration inside model or
source directories. `init` refuses nonempty configuration directories and never
replaces existing identities. It reads the current Zenith profile; select the
intended existing model/profile before taking the snapshot. A pinned revision
and exact adapter/tokenizer compatibility are required; no automatic download or
model activation occurs. The configuration snapshot and four separate service
key files remain private and must never enter Git, logs or model prompts.

The endpoint binds `127.0.0.1:8781`. All routes require a dedicated Bearer service
credential: `/healthz`, `/readyz`, `/v1/models`, `/v1/chat/completions`. Credentials
are loaded from owner-only files at startup. Restart with reviewed credential
files for rotation. They do not authenticate to the Zenith owner/admin API.
There is no public bind flag, permissive CORS, shell, training or tool executor.
Use a separate explicitly reviewed TLS deployment for remote access; it is not
implemented by these local commands.

Chat supports text, complete system/user/assistant/tool history, one completion,
actual tokenizer counts, native EOS/output budgets, standard SSE text and buffered
validated tool-call deltas. Call ids are preserved in requests and generated
uniquely for actual model calls. The inference service never executes them.
The saved Qwen tool protocol is supported; arbitrary templates are not declared
compatible. A required/forced call is validated rather than fabricated. Invalid,
unknown or truncated tool calls fail closed. `response_format` JSON constraints
are communicated to the model and validated; this is not constrained decoding.

Unsupported inputs fail explicitly: image/audio, proprietary reasoning settings,
custom stop strings, multiple choices, remote/recursive schema references and
regular-expression schemas. Schemas and requests are bounded. No history is
silently discarded to fit context. Owner-selected `--context-tokens`,
`--max-output-tokens` and `--deadline-seconds` affect only this separate service.
Defaults preserve the captured input/output budgets. Architectural context limits
remain enforced.

One generation is admitted at a time; concurrent calls receive 429, not an
unbounded queue. SDK callers must use bounded pure-inference retries. Disconnects
and deadlines cancel at model token boundaries, and the slot stays owned until
the worker has actually finished. This is cooperative cancellation, not a hard
kernel/GPU kill guarantee. An independent process/container supervisor is needed
for hard resource limits. Tool/schema streaming is deliberately buffered until
validation; ordinary text is streamed during generation.

## Verification and rollback

Unit tests use explicitly identified deterministic fixtures. The separate
`tests/integration/native_acceptance.py` uses the real checkpoint, real TCP,
OpenAI SDK, original Zenith account API and bridge: arithmetic, streaming, actual
tool/result round trip, disconnect recovery, login revocation, idempotency and
artifact/profile preservation. Install the `test` extra to run it:

```bash
uv sync --project integrations/inference_service --frozen --extra local --extra test
uv run --project integrations/inference_service --frozen --extra local --extra test python integrations/inference_service/tests/integration/native_acceptance.py --output native-acceptance.json
```

Stop this service with Ctrl+C. Removing its new environment/configuration leaves
original models, adapters, activation receipts and the ordinary Zenith app intact.
Do not delete or roll back native checkpoint files to remove this endpoint.


An optional `serve --queue-size 4` reserves up to four waiting requests for
parallel native analysts while keeping exactly one model generation active.
The default remains zero waiting slots. The queue is bounded to eight, expires
at the configured deadline, releases disconnected/cancelled waiters and rejects
overflow with 429. Waiting does not execute model work or consume output tokens.
Actual concurrent SDK requests and cleanup are tested; no throughput or
latency improvement is claimed. A queued request's wait and its subsequent
generation each have a separate bounded deadline.
