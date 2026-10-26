# Isolated Python execution (optional)

Zenith retains its selected model, tokenizer, adapters, checkpoint lineage, account
data, normal install and ordinary chat. This milestone extends the existing
execution controls with `sandbox-python`; it does not retrain a model or enable
model-generated tool execution. The feature is disabled by default.

## Prerequisites and trust boundary

Use a local Linux Docker daemon at `/var/run/docker.sock`, builtin seccomp and
cgroup v2 with CPU/memory/process limits. The server operator and Docker daemon are
trusted. Use an operator-reviewed public/runtime-only image containing Python;
never use an image with credentials, private user data, declared volumes or
unrecognized environment names. Review its licenses and provenance. No image is
downloaded or built by the tool. Windows orchestration currently rejects this
backend; ordinary Windows chat and the restricted numeric verifier keep working.
VM isolation, host workspace access, shell/Git tools, package installation and
network-enabled execution are not provided by this milestone.

Example preparation in Linux Bash (a deliberate operator download):

```bash
docker pull python:3.12-slim
sandbox_image="$(docker image inspect --format '{{.Id}}' python:3.12-slim)"
export ZENITH_SANDBOX_IMAGE="$sandbox_image"
export ZENITH_SANDBOX_ENABLED=true
export ZENITH_PLATFORM_ENABLED=true
export ZENITH_PLATFORM_RUNTIME_ENABLED=true
export ZENITH_PLATFORM_TOOLS_ENABLED=true
```

Review and retain the resolved immutable image ID for reproducibility. A mutable
image tag cannot be configured as `ZENITH_SANDBOX_IMAGE`. A missing image, daemon,
supported platform or isolation prerequisite fails closed. There is no host
Python fallback. These variables enable infrastructure, not account privileges.

Log in using the existing account/owner flow, verify owner MFA and obtain a
short-lived `sandbox-python` capability grant with `{"kind":"offline"}` scope.
Submit an explicit supervised task through the authenticated gateway:

```json
{"kind":"diagnostics","steps":[{"tool":"sandbox-python","arguments":{"source":"print(sum(x*x for x in range(10)))"}}]}
```

`POST /api/platform/tasks` accepts the task only with current owner/session/MFA,
capability and feature policy. The worker pauses for a one-use exact-action
approval. Review the submitted source and task, then approve its ID through
`POST /api/platform/approvals/{id}` with `{"approved":true}` in the same current
owner session. A model response or shared gateway bearer cannot grant permission.
Legacy owner-only direct execution also requires the explicit source-bearing
request, enabled backend, MFA and capability. Ordinary chat never calls this tool.

## Enforced bounds

- 1–8192 UTF-8 bytes of source; callers cannot select Docker arguments, image,
  environment, host paths, volumes, commands or network.
- Nonroot UID/GID 65534, all capabilities dropped, no-new-privileges, builtin
  seccomp, private cgroup namespace, no IPC sharing, readonly image filesystem.
- Network `none`; no host mounts, sockets, model/config directories or credentials.
  Image environment names are screened; runtime environment and proxy variables
  are cleared. The approved image itself must contain no secrets.
- Ephemeral `/work` and `/tmp` tmpfs (16 MiB each, noexec/nosuid/nodev); no retained
  workspace. CPU 0.5, memory+swap 128 MiB, 32 process limit, bounded descriptors.
- One execution slot per server process; concurrent direct calls are rejected.
  Deploy one such server process per controlled daemon; a shared multi-process
  sandbox admission service is not provided in this milestone.
- Program wall time defaults to 10 seconds (`ZENITH_SANDBOX_SECONDS`, 1–30).
  Docker control operations have separate five-second deadlines, so total latency
  includes setup, inspection and cleanup. Combined stdout/stderr is limited to
  2048 bytes; overflow aborts execution. Docker logs are disabled.
- Live authority and cancellation are checked during attachment. Revocation,
  emergency stop, time/output limits and failures trigger forced container
  cleanup; uncertain cleanup becomes an error requiring operator reconciliation.
  Arbitrary kernel/runtime exploits are outside these finite guarantees.

The output reports actual exit code, stdout/stderr, image, backend, network and
elapsed time. A nonzero program exit is reported as failed; completing a diagnostic
task does not mean its submitted program passed. Code is untrusted; do not submit
secrets. Existing redaction only recognizes configured/known patterns, not every
possible secret. Containers share the host kernel and are not equivalent to VMs.

## Verification and rollback

Run `python -m scripts.smoke_sandbox --image "$sandbox_image"` from the installed
Zenith environment. It uses real containers, temporary local accounts and SQLite,
MFA, scoped grants and one-use approvals; it does not load or change models or
production configuration. It verifies actual Python results, UID/capabilities,
no-new-privileges, observed cgroup limits, host-file and owned-listener isolation,
readonly root, cleared environment, ephemeral storage, cancellation/quotas,
authorization and cleanup. These are finite regression probes, not universal
sandbox-escape certification. Raw local results are in `sandbox-smoke.json`.
CI repeats the full smoke against its freshly built immutable application image.

Rollback: set `ZENITH_SANDBOX_ENABLED=false`, stop new task admission, cancel/drain
owned tasks and revoke its grants. Keep receipts and audit history. Inspect any
`needs_reconciliation` task and only the specifically recorded sandbox container;
do not blindly retry an uncertain effect. No schema or model migration is needed.
