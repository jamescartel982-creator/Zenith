# Deploy Zenith

## Your computer

Use the [Windows/Linux installer](local-installation.md) and run `zenith serve` through your wrapper. Open http://127.0.0.1:7860. Loopback needs no shared server token by default. `serve --warmup` loads/exercises the first contributor before startup; otherwise the first generation loads it. `/healthz` reports process health, version, and loaded state, not guaranteed answer quality or runtime availability.

## Docker / a server

1. Copy `.env.example` to `.env`.
2. Generate your own server token with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and set `ZENITH_API_TOKEN`. Do not commit it.
3. Run `docker compose up --build -d`.
4. Open http://127.0.0.1:7860 and enter it under **Server access**.
5. Create your local browser account; inspect logs with `docker compose logs -f zenith`.

The image installs a regular Zenith wheel and the `zenith` command, runs as UID 1000, and includes runtime resources, documentation, sample configuration, attribution, and all vendored support files. Model weights download separately. It excludes local secrets, private data, build output, and trained artifacts.

```text
docker compose exec zenith zenith --version
docker compose exec zenith zenith verify
docker compose exec zenith zenith system
```

Compose preserves the database in `zenith-data`, weights in `zenith-models`, and the profile/owner-code directory at **`/app/data/profile` inside `zenith-data`**. `docker compose down` retains volumes; `down -v` deletes them. Back up volumes before intentional removal. Mount adapters read-only under `/app/artifacts` and explicitly set `ZENITH_ADAPTER`, matching base model/revision, in a Compose override.

The `.env` options forwarded by Compose include provider, primary model/revision, context/output limits, Fast/Thorough, Auto/Brief/Full, brief-token/history caps, CPU threads, temperature, and retrieval count. Custom team JSON, adapters, or endpoint settings require an explicit override and appropriate mounts. Merely placing arbitrary variables in `.env` does not automatically expose them to a container.

The supplied image uses CPU PyTorch. GPU inference needs a compatible CUDA build/image and NVIDIA runtime; passing `--gpus all` to a CPU wheel does not add CUDA support. A quantized local runtime outside this image is another option. Allow roughly 4–6 GB available RAM for the small single model, or up to 6–8 GB for the complete small team. Larger models/contexts need more.

Use **one process and one replica** per database/model instance; locks are process-local. The server admits one generation and returns 429 while busy. Stop/cancellation joins local generation before reuse; cleanup can wait for a native forward pass or pending HTTP read.

The entrypoint runs `zenith serve --host 0.0.0.0 --port ${PORT:-7860}` and rejects public binds without a 32-character server token. The healthcheck uses `/healthz`. Keep this entrypoint; a custom direct Uvicorn command bypasses its bind check. On a public host, use HTTPS, a persistent `/app/data` disk, and an appropriate model cache. Compose binds only to host loopback by default.

## Owner workspace in Docker

After creating your browser account:

```text
docker compose exec zenith zenith admin init --username YOUR_USERNAME
```

Read the reported code file privately in your own container terminal, then sign in as that account and unlock Admin. Never paste the code into public logs or messages. It is independent of the shared server token. Elevation lasts 15 minutes; [owner access](admin.md) documents rotation and the bounded Devil-mode tools.

Older images stored the owner-code file outside the data volume. When upgrading one of those installations, deliberately generate a replacement with `admin init --username YOUR_USERNAME --rotate`; the persisted account/password, memories, and conversation database remain. New images keep the replacement in the data volume across recreation. Backups include private user data and must be protected.

## Hugging Face Docker Space

The README includes `sdk: docker` and port 7860 metadata. Create a Docker Space, copy the repository's source/deployment files while retaining licenses, set secret `ZENITH_API_TOKEN`, choose fitting CPU hardware, and attach persistent storage. With Space storage, set `AGENT_DATA_DIR=/data/zenith`, `ZENITH_HOME=/data/zenith/profile`, and `HF_HOME=/data/huggingface`. Ephemeral disks can reset accounts, codes, and downloads. No Space was created automatically.

## Authentication and JSON API

There are separate layers:

| Layer | Purpose |
| --- | --- |
| Optional `Authorization: Bearer <server-token>` | Shared server gate, required when configured; not an AI provider key |
| HttpOnly `zenith_login` cookie | Local password account; owns its conversations, notes, feedback, and private metrics |
| Owner account plus private code | Short-lived admin elevation for tools, server metrics, and human reviews |

Use same-origin HTTPS in a public deployment. POST login/register returns the cookie; subsequent API requests must retain it. Signed-in conversation access is checked by account ownership. Anonymous conversations retain unguessable UUID access and cannot be claimed by another account. The server operator controls the database and is still a trusted administrator.

- `POST /api/chat`: `{ "session_id": "<uuid>", "message": "Hello", "response_mode": "fast", "reply_style": "auto", "skill": "general" }`.
- `POST /api/chat/stream`: same body, SSE `start`, `delta`, `result`, or sanitized `error` events. Completed results include quality, source, timing, and reported-usage metadata.
- `GET /api/history/<uuid>`, `DELETE /api/history/<uuid>`: owned history; deletion removes future training approvals and linked reviews/metrics, not existing exports/weights.
- `POST /api/feedback`: explicit rating/correction/training approval; an approval must be intentional.
- `GET /api/account`, `POST /api/account/register`, `/login`, `/logout`: local account lifecycle.
- `POST /api/skills/command`, `GET /api/skills/current?session_id=UUID`: conversation-scoped `/skill` activation and status. Security selection requires the unlocked owner; both chat endpoints enforce the same rule and use saved selection when `skill` is omitted. See [skill commands](skills.md).
- `GET/POST /api/memories`, `DELETE /api/memories[/<uuid>]`: signed-in private saved notes.
- `GET /api/system`, `/api/team`, `/api/catalog`, `/api/model-packs`, `/api/knowledge`, `/api/skills`: configured components and reference metadata.
- `GET /api/metrics`: that account's private aggregates. `/api/admin/metrics` requires current owner elevation.
- `POST /api/review-requests`, `GET /api/review-requests`: explicit local human-review requests; admin review/resolve endpoints require elevation.
- `GET /healthz`: public process/model-loaded status and release version; no generation.

The browser stores the shared token/conversation ID in tab session storage and a last-conversation identifier per account locally; the login cookie is HttpOnly. Saved account history survives reload and is listed after login. No external reviewer is notified automatically. See [accounts/memory](memory.md) and [System/monitoring](system.md).

## Troubleshooting

- **503:** check model download, dependencies, RAM, adapter/base match, or the local runtime. Provider errors are sanitized for clients.
- **401:** enter the configured shared gate token and sign in for private features.
- **403 on admin:** sign in as the configured owner and unlock with its private code; text prompts cannot grant roles.
- **429:** wait for generation/cleanup, then retry. Failed text remains in the composer.
- **Context error:** shorten the message or increase `CONTEXT_TOKENS` within hardware/model limits; oldest complete turns are trimmed first.
- **Truncated answer:** select Full, continue explicitly, or adjust the operator output limit.
- **Interrupted stream:** check the local runtime's logs and retry. EOF without a completion marker fails the turn and saves no partial answer; see [provider reliability](provider-reliability.md).
- **Integrity failure:** inspect the listed files and reinstall/re-extract the intended version. Do not regenerate checksums to hide an unknown change.
- **Training skips every row:** inspect length/format limits and use independent approved examples.
- **Tiny nonsense:** a random or barely trained scratch transformer is not a capable pretrained assistant.
