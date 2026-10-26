# Independent sandbox deadline validation — 0.17.2

2026-10-26. A real forced-controller-loss probe reproduced an active Python
container continuing beyond its two-second configured budget in 0.17.1. The
fixture was explicitly removed; no user model/data was modified.

The container now runs a separate nonroot PID-1 supervisor. Its trusted deadline
starts before stdin is read; submitted code runs in a child process and cannot
edit the timer's Python objects. When PID 1 exits with reserved code 124, remaining
namespace processes stop. The existing host watchdog, authorization checks,
quotas, disabled network, readonly/no-host-mount boundaries and cleanup remain.
A dead host controller can leave stopped metadata requiring scoped operator
reconciliation; the new labels identify only owned sandbox containers. This is
not a VM or universal kernel/signal/escape-resistance claim.

Validation:

- **308 tests: 307 passed, one skipped; 43.514 seconds.**
  [Raw suite](watchdog-tests.log).
- **Ten real Docker probes passed**, including killing the actual controller
  process while its owned container was running, then observing that container
  exit with code 124 independently. The fixture removes only its owned stopped
  container afterward; no sandbox containers remain.
  [Raw results](watchdog-smoke.json).
- The other probes retain actual UID/capabilities/no-new-privileges/environment,
  cgroup CPU/memory/process limits, host-file/listener isolation, temporary
  workspace, wall/output quotas, owner/MFA/exact-approval and emergency-stop
  coverage. No model calls, training or live profile changes occur in this smoke.
- Windows/Linux installation, actual trained-model inference and container checks
  remain in CI; the Docker/account suite now includes this crash probe.

All restricted execution remains disabled by default. Roll back by disabling
ZENITH_SANDBOX_ENABLED, revoking grants and cancelling/draining tasks while
retaining receipts and reviewing uncertain containers. Rolling back this fix
reintroduces the controller-loss limitation; keep the tool disabled in that case.
No schema, tokenizer, weight or adapter migration is involved. Current repository
URLs remain https://github.com/n8storm/Zenith.
