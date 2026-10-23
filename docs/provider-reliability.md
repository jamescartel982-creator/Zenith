# Model provider reliability

Zenith separates request admission and persistence (`agent/core.py`), model-specific inference (`agent/providers.py`), and bounded HTTP framing (`agent/transport.py`). Providers return text and the exact messages used; token counts come from the model/runtime rather than estimated character counts. Fast/Thorough and per-request token budgets still use the same admission lock and cached providers.

## Completion is explicit

Ollama streams use newline-delimited JSON and must produce `done: true`. OpenAI-compatible local runtimes use SSE: a complete `[DONE]` event or a complete choice event with `finish_reason: stop` or `length` establishes completion. A length finish means the configured output cap was reached; the user can request continuation. Tool-call or other unsupported finish reasons produce an error because this chat path does not execute model tools.

An ordinary TCP EOF is insufficient. Malformed JSON, invalid UTF-8, unsupported text shapes, an upstream error, an incomplete SSE event, or EOF before a completion marker fail the turn. Any partial text already displayed is temporary: the API emits an error, saves no partial conversation turn, records failure metadata, and releases the generation lock. Retry is explicit; Zenith does not silently repeat a partially delivered request.

Usage metadata is committed only after stream completion. A local server can send a usage-only SSE event after its finish event. Missing or invalid numeric token counts remain unknown. No credentials or upstream error payloads are incorporated into generated text by the protocol parser.

## Transport bounds and cleanup

- Maximum UTF-8 line or assembled SSE data event: **1 MiB**. Maximum streamed HTTP body after decompression: **8 MiB**, including heartbeat traffic. Application text also retains its existing **150,000-character** cap.
- Split Unicode bytes, CR/LF/CRLF line endings, an initial UTF-8 BOM, SSE comments and metadata, and multiline `data:` fields are supported. SSE events require a blank-line delimiter.
- Requests reads arriving bytes without waiting for its default 512-byte line buffer. This prevents artificial buffering on a runtime that flushes a small event and waits. It does not accelerate neural inference.
- Responses close on normal completion, parser failure, cancellation, or early generator closure. Redirects are disabled for both HTTP providers; Zenith sends no provider API key.
- Existing network timeouts are **10 seconds to connect** and **300 seconds of read inactivity**. They are not a total request deadline. Cancellation is checked as bytes/events arrive; a stalled blocking read can wait for its read timeout. Hugging Face generation stops cooperatively between decoding steps; model loading and a running device kernel are not forcibly interrupted.

Use one server worker per local model process. The current admission policy returns HTTP 429 when generation is occupied; it is not a distributed job queue. GPU/MPS execution, large-model throughput, long-running reliability, and an actual Ollama/vLLM/llama.cpp deployment need separate validation on the intended hardware/runtime.

## Reproduce the checks

```bash
python -m unittest discover -s tests -p test_provider_transport.py -v
python -m unittest discover -s tests -v
zenith verify --source .
```

Protocol fixtures cover completion, truncation, malformed events, Unicode boundaries, byte limits, provider usage, redirects, and cancellation. A real loopback HTTP server verifies early text without waiting for the remainder; another test sends an incomplete stream through the actual chat API and verifies the error, absent history turn, released lock, and successful next request. These tests check application behavior; they do not measure answer accuracy or model capability. Historical model evaluations retain their original scope in [validation](validation.md).
