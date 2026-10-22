# Deploy Zenith

## Your computer

Install `.[local]` and run `python -m agent.server`, then open http://127.0.0.1:7860. The default configuration needs no access token while bound to loopback. First inference downloads the selected model. `GET /healthz` reports process health and whether the model has loaded; process health does not claim inference readiness.

## Docker / a server

1. Copy `.env.example` to `.env`.
2. Generate a random token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and put it in `ZENITH_API_TOKEN`. Do not put real tokens in Git.
3. Run `docker compose up --build -d`.
4. Open http://127.0.0.1:7860 and enter the token under **Server access**.
5. Inspect logs with `docker compose logs -f zenith`.

Compose persists the SQLite database in `zenith-data` and downloaded weights in `zenith-models`. `docker compose down` preserves them; `docker compose down -v` deletes them. Back up volumes before deleting them.

The supplied image uses CPU PyTorch. GPU deployment needs a compatible CUDA PyTorch image/build and NVIDIA runtime; merely passing `--gpus all` to this CPU image does not provide CUDA inference. Ollama with a quantized model is another option for local GPU inference outside this image.

For a hosted server, point a TLS reverse proxy to port 7860, keep a long access token, attach persistent storage at `/app/data`, and cache model files at `/home/zenith/.cache/huggingface`. Start with at least 4–6 GB available RAM for the 0.5B default; concurrent infrastructure and larger contexts increase memory. The application admits one generation at a time and returns 429 while busy. Run **one process and one replica** per database/model instance; locks are process-local.

Set `PORT` if the host assigns an HTTP port. The image starts `python -m agent.server --host 0.0.0.0 --port ${PORT:-7860}` and checks `/healthz`. Public binds through this entrypoint reject tokens shorter than 32 characters. Use the provided entrypoint; a custom direct Uvicorn invocation bypasses that CLI bind check.

To serve an adapter in Docker, bind-mount its folder read-only under `/app/artifacts` and set `ZENITH_ADAPTER` to that path. Keep the matching `HF_MODEL` and `HF_REVISION`. Do not put datasets in a public image.

## Hugging Face Docker Space

The root README includes `sdk: docker` and `app_port: 7860` metadata. To publish:

1. Create a **Docker Space** in your Hugging Face account.
2. Copy this branch's source, Dockerfile, requirements files, and root README into that Space repository. Preserve its metadata.
3. In Space Settings, add **secret** `ZENITH_API_TOKEN` with a long random value. Set `HF_MODEL` if selecting another checkpoint.
4. Choose hardware that fits the model. First chat downloads weights. The provided image is CPU-only.
5. For persistence, add Space persistent storage and set `AGENT_DATA_DIR=/data/zenith` and `HF_HOME=/data/huggingface`. Space disk without persistent storage is ephemeral and can reset.
6. Open the Space and enter your token in **Server access**. Keep it private if the assistant is personal.

A Space has not been created automatically: it needs the destination account and its hosting configuration. Server conversation approvals authorize local training exports, not public dataset publication.

## JSON API

The API takes a UUID `session_id` that acts as an unguessable conversation identifier. Keep it private. Every API route requires `Authorization: Bearer <token>` when a server token is configured. The token is a single-owner credential, not separate user accounts.

- `POST /api/chat`: `{ "session_id": "<uuid>", "message": "Hello" }`
- `GET /api/history/<uuid>`: last 100 turns in the conversation.
- `POST /api/feedback`: `{ "session_id": "<uuid>", "turn_id": "<uuid>", "rating": "good", "approved": true, "correction": null }`
- `DELETE /api/history/<uuid>`: removes conversation turns and their future export approvals.
- `GET /healthz`: public process/model status; does not run generation.

The browser keeps the token and conversation ID in tab session storage. A new conversation starts a new ID. Closing the tab loses that tab's resume identifier; it does not delete server history. Save the ID if you need to resume through the CLI's `--session` option. Session IDs separate context and feedback but are not a substitute for account authorization in a multi-user deployment.

## Troubleshooting

- **503 on chat:** check server logs. Common causes are an incomplete model download, insufficient memory, missing `.[local]` dependencies, or unreachable Ollama.
- **401:** open Server access and enter the exact configured token.
- **429:** wait for the current generation and retry. The original text remains in the composer on failure.
- **Context budget error:** shorten the message or increase `CONTEXT_TOKENS` within the model/hardware limit. The server drops complete oldest turns before rejecting a current message that cannot fit.
- **Adapter mismatch:** select the base model used to train it; keep the recorded base revision. Adapters do not replace base weights.
- **Training skips every row:** increase `--max-length` if hardware allows, or approve shorter examples.
- **Tiny output is nonsense:** this is expected from random or barely trained weights. Use the pretrained HF default for useful conversation.
