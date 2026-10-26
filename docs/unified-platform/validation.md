# Zenith 0.17 validation and limits

2026-10-25. PR18 (reasoning) and PR19 (supervised tasks) are merged into main.
Their combined head passed all seven Windows/Linux Python3.10/3.12,
installed-model inference and container checks before merge:
https://github.com/jamescartel982-creator/Zenith/actions/runs/40223216020
The diagnostic watch also passed:
https://github.com/jamescartel982-creator/Zenith/actions/runs/40223216101

## Isolated Python milestone

- Final local suite: **308 tests run, 307 passed, one skipped, 47.683 seconds**.
  Raw output: [sandbox-tests.log](sandbox-tests.log).
- Nine **real Docker** acceptance probes passed, including observed nonroot UID,
  no capabilities, no-new-privileges, readonly root, cleared environment,
  inaccessible host canary/socket/listener, actual 128MiB/32-process/0.5-CPU
  cgroup limits, ephemeral workspaces, output/wall-time limits, lifecycle
  revocation, and owner/MFA/grant/exact-approval task execution. Emergency stop
  during an approved task aborts it with conservative reconciliation state; no
  sandbox containers remain. [Raw results](sandbox-smoke.json).
- Tested backend: Linux Docker28.4.0, cgroupv2, builtin seccomp; Python3.12-slim
  immutable image ID is recorded in the raw results. The official pulled image
  index digest was sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704.
  CI repeats the full account/backend smoke using its own freshly built pinned
  Zenith image. Windows text functionality remains supported; this Unix-socket
  backend is explicitly unavailable to a native Windows server.
- `pip check`: **No broken requirements found** in the existing development
  environment. No new mandatory Python dependency was added.
- Weight, adapter/tokenizer and saved-profile before/after receipts match.
  [Public protection record](sandbox-protection.json) omits private receipt data.
  No model replacement, retraining or new candidate promotion occurred. The
  existing selected adapter remains experimental with its failed numerical
  quality gates retained; installation/test success cannot relabel those gates.
- Actual unchanged cached HF+LoRA queue/native smoke (one pair): matching outputs;
  direct 4226.268ms, queued 7307.406ms. Queued was slower. This measurement preceded
  the final sandbox-only admission-limit/docs changes; inference implementation
  is unchanged. [Raw result](sandbox-native-queue.json). No general quality,
  acceleration, token-saving or reference-parity gain is claimed.

## Remaining scope and rollback

The [current progress overlay](progress.json) advances only the bounded offline
Python contract. The [approved audit](../unified-audit/README.md) remains an
immutable historical inventory. Its broad Docker/Python/file/shell reference
rows are not fully satisfied by this narrow backend. Autonomous model-generated
tools, host workspaces, general shell/Git, reviewed skill learning, new retrieval,
plugins/MCP, multi-agent isolation, schedulers, channels, browser/computer tools,
new media and platform applications still require their planned implementations
and actual supported-environment acceptance. External services/devices are not
verified by these tests. Finite isolation probes are not universal escape or
prompt-injection certification.

All new restricted tools default off. Disable ZENITH_SANDBOX_ENABLED, stop task
admission, revoke grants and drain/cancel workers to roll back this milestone.
Retain receipts and review uncertain tasks rather than replaying them. No schema,
original checkpoint or existing user-data migration is needed. Earlier branches,
production model files and the ordinary clone/install.py/run launcher flow are
preserved. The workspace disk was recovered by removing only unused untagged
historical Docker build images, not model caches, checkpoints or user data.
