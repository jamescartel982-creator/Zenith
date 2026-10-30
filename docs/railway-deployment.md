# Railway backend deployment

The repository's root `Dockerfile` has an optional BuildKit secret mount for a
managed build proxy CA. Railway rejected that instruction before installing
dependencies: `other mount types are not supported` at line 27. Removing TLS
verification or putting credentials in build arguments is not a fix.

`deploy/railway/Dockerfile` provides an equivalent CPU/non-root
image without the optional secret mount or proxy-specific CA configuration.
Build context remains the repository root. The original Dockerfile remains
available for ordinary Docker and managed environments. GitHub CI builds and
runs package, HTTP, authorization and persistence tests for both images.
The Railway image also maps the original workspace profile path
`/home/agent/.local/share/zenith` to `/app/data/profile`, preserving references
in immutable approval receipts while keeping the restored state on one volume.

For an existing service, set the service variable
`RAILWAY_DOCKERFILE_PATH=deploy/railway/Dockerfile` and its Dockerfile path to
`deploy/railway/Dockerfile`. Ensure it deploys a commit containing that file.
This uses the provider's documented
[custom Dockerfile selection](https://docs.railway.com/builds/dockerfiles#custom-dockerfile-path)
without adding a legacy `railway.json` file. The current CLI warns that legacy
config-as-code files stop working after 2026-12-01. Do not select `agent/web` as
a static deployment directory.

## Preserve the actual deployment state

A successful image build is not an activated trained model. The image's generic
defaults do not carry your private saved profile, database, trained adapter or
approval receipt. Before enabling production inference:

1. Snapshot the existing SQLite database with SQLite's backup API; verify
   integrity. Keep profile and model artifacts private and verify their hashes.
2. Attach durable storage and restore a **copy** of that state. Keep the paths
   referenced by immutable checkpoint receipts valid. Never replace original
   files or deploy the default base model as a substitute for the active adapter.
3. Set the exact existing `AI_PROVIDER`, `HF_MODEL`, `HF_REVISION`,
   `ZENITH_ADAPTER`, `ZENITH_CHECKPOINT_RECEIPT`, `ZENITH_HOME`, `AGENT_DATA_DIR`
   and model-cache mounts. Verify the receipt using the existing
   `agent.deployment.validate_activation` before starting inference.
4. Configure independent `ZENITH_API_TOKEN` and `ZENITH_ORIGIN_SECRET` through
   Railway runtime secrets; never store them in Git, build arguments or logs.
5. For the Cloudflare gateway, use
   `python -m agent.cloudflare_origin --host 0.0.0.0` as the start command. It
   reads Railway's `PORT` automatically. Include the public Worker hostname in
   `ZENITH_ALLOWED_HOSTS`, without a scheme or path.
6. Use one process/replica for the local SQLite/model instance and disable
   application sleeping for continuously running service. Verify plan capacity;
   a trial or small free allocation does not promise permanent 24/7 inference.
7. Set the Worker's `ZENITH_BACKEND_URL` to the actual generated Railway HTTPS
   root and its `ZENITH_ORIGIN_SECRET` to the matching secret. Preserve user
   authentication and all owner controls. See
   [Cloudflare deployment](cloudflare-deployment.md) for runtime settings.

The normal image healthcheck expects the ordinary private `zenith serve`
entry point. When selecting the authenticated origin adapter, use a health
probe with its origin secret and public-origin headers, as in
`deploy/cloudflare/compose.origin.yaml`. Do not configure Railway's unauthenticated
HTTP probe to expect a 200 from the protected `/healthz`; verify the authenticated
endpoint separately. No direct origin access should bypass gateway authentication.

## Acceptance and rollback

Wait for Railway's terminal `SUCCESS`, then verify the authenticated backend
health response, an actual trained-model answer through the Worker, account
isolation and preserved data after restart. `BUILDING`, image validation alone
and a generic `/healthz` response are insufficient to claim model deployment.

Keep the previous deployment and a private database/model snapshot. Roll back
the service release and matching Worker configuration without deleting volumes.
If reverting to the root Dockerfile on Railway, the original unsupported mount
failure will return. This change does not retrain, merge or overwrite weights.
