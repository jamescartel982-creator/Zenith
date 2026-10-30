# Cloudflare deployment audit and implementation plan

Audited source: `a90d9e6daf88dfc380d1a81c0951bc6947e631b8` (security release 0.17.5).
No model, tokenizer, checkpoint, database or upstream runtime is changed.

## Root cause and architecture choice

The configured command is `npx wrangler deploy`. The repository had no
`wrangler.jsonc`, root Node manifest, Worker entry point or root static-output
directory. Its existing frontend is `agent/web/index.html`, `app.js`, `style.css`
and images, served by `agent/server.py` at `/` and `/static`. Guessing that the
repository is a static site produces the reported directory-detection failure.
Pointing assets at that directory alone would publish a page without its APIs.

`requirements.txt` contains FastAPI, Uvicorn, authentication and HTTP libraries.
`requirements-local.txt`/`pyproject.toml` add native PyTorch/Transformers/PEFT.
`agent/providers.py` performs local threaded inference, `storage.py` uses a
persistent local SQLite database, and agent execution can use host/container
facilities. `Dockerfile` already runs a non-root Python service with `/healthz`;
`compose.yaml` retains data and model-cache volumes and binds to loopback.

Python Workers support FastAPI through a Workers ASGI adapter and compatible
Python/PyEmscripten packages. That does not make this project's native PyTorch,
filesystem persistence and process/tool execution portable unchanged. A static
frontend/API split would introduce cross-origin authentication and duplicate
asset deployment. Chosen design: **a small Worker gateway in front of the
unchanged separately hosted Python application**, serving all paths through one
public origin. Cloudflare Tunnel may additionally protect/reach that origin.

## Exact file-by-file plan

| Destination | Dependencies and behavior | Tests | Rollback |
| --- | --- | --- | --- |
| `wrangler.jsonc` | Explicit `main`, date, existing Worker name `zenith`; preserve dashboard vars; no static autodetection or model bundling. | Actual Wrangler dry-run. | Restore previous Worker version/config. |
| `package.json`, `package-lock.json` | Test/deploy tooling only, Wrangler 4.156.0, Node >=22; no Python dependency merge. | `npm ci`, Node tests, dry-run. | Remove optional Node tooling. |
| `integrations/cloudflare/worker.mjs` | Fixed HTTPS backend, separate origin secret, strict Origin validation, bounded requests, response streaming, no redirects/cache, sanitized errors/logs. | Native Node tests plus real Wrangler/ASGI smoke. | Route back to prior reviewed Worker. |
| `agent/cloudflare_origin.py` | Optional authenticated ASGI envelope around `create_app`; validate public origin against allowed hosts, reject spoofing before trusting forwarded scheme/Host; keep app account/owner gates. | Actual FastAPI/SQLite fixture and gateway smoke. | Use original `zenith serve` on private origin. |
| `agent/redaction.py` | Recognize the new configured origin credential as a secret; no model changes. | Existing credential suite and origin tests. | Remove new environment-name entry only with adapter disabled. |
| `deploy/cloudflare/compose.origin.yaml` | Explicit opt-in command/env overlay on existing service and volumes. Keep model/profile mounts and selections; never run volume deletion. | Compose configuration validation and deployment docs. | Omit overlay; retain all volumes. |
| `tests/test_cloudflare_origin.py`, `integrations/cloudflare/test_worker.mjs` | Authentication, CSRF, host, credential, bounds, timeout, health, streaming regressions. | Execute tests. | Disable gateway; keep regression tests. |
| `scripts/smoke_cloudflare.py` | Real local Wrangler runtime to real isolated FastAPI app, labeled fixture model. No production account/data access. | Run locally and in CI. | No production state to undo. |
| `.github/workflows/cloudflare.yml` | Pinned SDK, tests, dry-run, local runtime smoke; no deployment credentials. | Observe successful jobs. | Disable optional workflow. |
| `docs/cloudflare-deployment.md`, `docs/deployment.md`, `README.md`, `.gitignore`, `.dockerignore`, `release-manifest.json` | Configuration, secret provisioning, health, persistent hosting, measured evidence, rollback; exclude local SDK/state/secrets from Git and build context. | Manifest/source verification, command checks. | Restore docs/manifest with matching source. |

The backend must keep its actual existing model/revision, adapter and persistent
profile/data mounts. This plan does not silently initialize an empty remote
database or switch to a default untrained/different model.

## Deployment prerequisites and boundaries

No Cloudflare CLI credentials are configured in this execution environment.
The Railway connection currently requires reauthentication; no accessible
existing backend address has been discovered. A live deployment therefore needs
the operator's backend URL and authorized Cloudflare account connection.
Credentials belong in environment/platform secrets, never Git or chat.

Local validation can establish that the error is fixed and the gateway works;
it cannot establish public availability until an authenticated deploy succeeds
and the real public health/auth/inference checks pass. Unconfigured gateways
fail closed rather than returning fake model answers. Protected origin and API
credentials are independent; the gateway never inserts an owner or user token.

## Official references consulted

- https://developers.cloudflare.com/workers/wrangler/configuration/
- https://developers.cloudflare.com/workers/languages/python/
- https://developers.cloudflare.com/workers/languages/python/packages/
- https://developers.cloudflare.com/workers/languages/python/packages/fastapi/

Cloudflare documentation retrieved 2026-10-30; Wrangler 4.156.0 resolved from npm
on that date and requires Node >=22. Historical Python-package limitations are
not treated as current documentation.
