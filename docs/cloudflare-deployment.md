# Deploy the existing Zenith through Cloudflare

The [audit and file plan](cloudflare-deployment-plan.md) records the original
failure and architecture decision. Cloudflare deploys a transport Worker;
Zenith remains a normal Python application with its existing model, APIs,
authentication, agents and persistent SQLite/profile/model storage.

```mermaid
flowchart LR
    Browser[HTTPS browser or API client] --> Worker[Cloudflare Worker gateway]
    Worker -->|HTTPS plus separate origin secret| Origin[Authenticated Python origin adapter]
    Origin --> App[Existing Zenith FastAPI and agents]
    App --> Model[Unchanged model and adapters]
    App --> Data[Existing private SQLite and profile volume]
```

## What fixes the build error

`wrangler.jsonc` declares `integrations/cloudflare/worker.mjs` as `main`.
Wrangler no longer guesses a static-output directory. The Worker forwards `/`,
`/static/*`, `/api/*` and `/healthz` to the Python origin, keeping UI and cookies
on one public HTTPS origin. There is no frontend copy, rewritten model, D1
migration or simulated model implementation.

Python Workers support FastAPI, but this project's native PyTorch inference,
persistent files and process/container tool execution are not an unchanged
Python Worker application. Uploading `requirements.txt` or only `agent/web`
would not deploy the complete existing system.

## Prepare the backend before publishing

Use an existing continuously running Linux/Docker host with sufficient RAM,
CPU/GPU, durable model cache and private persistent data. The existing small
CPU configuration generally needs 6–8 GiB; measure the actual chosen model.
Keep one process/replica per SQLite/model instance. This execution workspace
is not permanent hosting.

Keep the exact active model/revision, adapter mounts and profile paths from the
existing deployment. Back up private volumes and verify checkpoint hashes.
Do not start a fresh empty volume or accept default model settings as a
substitute for the existing Zenith checkpoint. Never copy keys, SQLite data or
weights into Git or a Worker bundle.

Configure these backend environment secrets/settings:

| Name | Purpose |
| --- | --- |
| `ZENITH_API_TOKEN` | Existing independent server access credential, at least 32 characters. |
| `ZENITH_ORIGIN_SECRET` | New independent random 32–256 URL-safe characters; only Worker and origin know it. |
| `ZENITH_ALLOWED_HOSTS` | Exact public Worker/custom hostname; include loopback hosts for maintenance if needed. No schemes, ports or wildcards. |
| `ZENITH_PUBLIC_ORIGIN` | Full public HTTPS origin, used by the optional Compose healthcheck. |
| Existing model/profile settings | Preserve provider, HF identifier/revision, adapter, data/profile/cache mounts and account state. |

For an existing Compose installation, use the **same Compose project and
existing volumes**, adding the overlay:

```bash
docker compose -f compose.yaml -f deploy/cloudflare/compose.origin.yaml config --quiet
docker compose -f compose.yaml -f deploy/cloudflare/compose.origin.yaml up -d --build
```

Retain any existing model-mount override files in both commands. The overlay
selects `python -m agent.cloudflare_origin` and supplies the new transport
configuration; it does not select another model or replace volumes. Protect
the loopback origin with a private HTTPS reverse proxy or named Cloudflare
Tunnel. A public Docker host must have a firewall and durable volumes.

For other platforms use the same existing image and optional entry point:

```bash
python -m agent.cloudflare_origin --host 0.0.0.0 --port 7860
```

That adapter rejects direct requests lacking the separate origin secret. Only
then does it validate and trust the public Host/HTTPS metadata supplied by the
Worker. It leaves the browser Origin and the application's account/owner gates
intact. Do not enable Uvicorn's arbitrary forwarded-header trust. The normal
`zenith serve` command remains unchanged for private installations.

The gateway copies Cloudflare's incoming `CF-Connecting-IP` into an overwritten,
authenticated transport header; the origin validates its IP type before using
it for rate limits. Arbitrary client `X-Forwarded-*`/`X-Zenith-*` values are
discarded. If Cloudflare removes visitor IP headers, limits conservatively share
the origin peer address. IP metadata never grants account or owner privileges.

## Configure and deploy the Worker

Use Node 24.19.0 (`.node-version`) and the lockfile's Wrangler 4.156.0:

```bash
npm ci
npm test
npm run check
```

The last command is a **local deployment dry-run**, not a live deployment.
Cloudflare builds can use build command `npm ci && npm test && npm run check`
and deployment command **`npx wrangler deploy`**, with repository root as the
working directory. The configuration's Worker name is `zenith`, matching the
existing failing build. `keep_vars` preserves dashboard variables; existing
secrets stay in Cloudflare. No account ID or token is committed.

Configure the Worker's `ZENITH_BACKEND_URL` to the backend's fixed HTTPS origin,
without credentials, a path, query or fragment. It must reach the authenticated
origin adapter, not another route back to this same Worker. Configure
`ZENITH_ORIGIN_SECRET` as a Worker secret with the same value as the backend:

```bash
npx wrangler secret put ZENITH_ORIGIN_SECRET
```

Enter it privately at the prompt or use the platform secret interface. Never
place secret values in command arguments, Git, query strings, logs or chat.
For CLI/CI authentication, configure least-privilege `CLOUDFLARE_API_TOKEN` and
`CLOUDFLARE_ACCOUNT_ID` through the execution platform's secret store. In an
interactive trusted local terminal, Cloudflare's supported OAuth login is an
alternative. Zenith's API token is not automatically inserted by the Worker;
clients still authenticate normally. No admin identity is granted by the edge.

Once the backend and secrets are ready, deploy:

```bash
npm run deploy
```

No backend or account is invented automatically. If runtime bindings are
missing, the deployed Worker returns a protected 503; this must not be described
as a working public Zenith installation. `ZENITH_TEST_LOOPBACK=1` is exclusively
for the isolated local test's loopback HTTP backend; never set it in production.
Public client traffic is HTTPS-only. Redirects from the backend are not followed
by the gateway. Cache bypass, bounded requests, header deadlines and native
response streaming protect the transport. Logs contain method/status/timing
and an opaque request ID, not request paths, bodies or credentials.

## Verify and monitor

- `GET /_edge/healthz`: gateway configuration/liveness only; does not claim that
  inference or the backend is healthy.
- `GET /healthz`: reaches the actual Python app, reporting its version/provider
  and model-loaded state. This is not an answer-quality benchmark.
- `/` and `/static/app.js`: must serve Zenith's original frontend.
- `/api/account` without server authentication: must return 401 on this public
  setup. Existing owner-only routes must remain inaccessible to ordinary users.
- Connect with the normal server gate, sign in and verify actual streamed model
  inference on the public URL before declaring deployment successful. Check that
  restart preserves the same account/database and model identity.

The local acceptance command starts **real Wrangler/Workerd and real FastAPI**:

```bash
python -m scripts.smoke_cloudflare --output /tmp/cloudflare-local.json
```

Its model is explicitly a fixture. It verifies original UI bytes, HTTPS cookies,
origin authentication, CSRF, owner denial, streamed/persisted secret redaction
and disconnect. It accepts only its generated local TLS certificate for this
isolated loopback test. Public verification must use normal certificate checks.
The CI workflow runs this acceptance plus Python/Worker tests and Wrangler
dry-run without production credentials. Passing local tests is not proof that
the public deployment is configured.

## Rollback and limits

Retain the previous Cloudflare Worker version before deploy and roll traffic
back through Cloudflare if validation fails. Restore the prior reviewed backend
image/command by removing the overlay; preserve all volumes and model mounts.
No database downgrade is needed. Rotate the origin secret on both sides together
if exposed. Never run a volume-deletion command to troubleshoot this integration.

The Worker is not an inference host, scheduler or permanent Python service.
Cloudflare proxy/time/plan limits and backend capacity still apply. It currently
transports the Zenith app's HTTP/SSE API; it does not claim to proxy every
independently deployed OpenClaw WebSocket interface. HTTPS, authentication and
headers reduce risk; they do not guarantee immunity to compromise.
