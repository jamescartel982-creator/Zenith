# Persistent Linux service management

This additive installer renders six unprivileged systemd user services, a group
target and a periodic process-liveness timer. It manages Zenith accounts/UI,
verified Zenith inference, the integration bridge, native Hermes, native
OpenClaw and the native TradingAgents research service. Each runtime keeps its
own environment, configuration, credentials and persistent data.

**Status:** service generation and native systemd syntax are tested. No
permanent host is configured, no reboot/soak test has run, and live brokerage is
not implemented by this installer. The owner has paused hosting activation.
The timer measures process liveness; it does not certify model readiness,
answer quality, financial accuracy or uptime.

## Prepare a host

Use a supported Linux host with systemd, persistent storage and a dedicated
unprivileged service account. The sample memory caps total roughly 15.5 GiB;
an initial host with 24 GiB RAM and 40 GiB free storage is a sizing estimate,
not a benchmark or capacity guarantee. Adapt caps after measuring actual use.
CPU execution is supported. Preserve previous releases and backups separately.

Use the existing [runtime setup](../../integrations/runtime_setup/README.md)
and independent inference, Hermes compatibility and TradingAgents instructions.
Keep upstream source pins and lockfiles:

| Component | Pinned source | Runtime |
| --- | --- | --- |
| OpenClaw | `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f` | Node 26.12.1, pnpm 12.15.0 |
| Hermes | `d05095663342556788cf2a198bfa7844cc7968ab` | Python 3.14.8; separate approved chat build |
| TradingAgents | `e8f5503e9b86d5c2710b0c76b1f686703968c9df` | Independently locked Python 3.12 environment |
| Zenith / bridge / inference | Record the reviewed release commit | Python 3.12 |

The native dependency environments must already contain the corresponding
Zenith additive distributions. This installer does not install dependencies,
download weights, initialize models, migrate databases or create accounts.
Preserve the selected trained checkpoint and tokenizer; inference verifies its
existing identity manifest on startup. Initialize a *new* private service
directory only when none exists; do not reset an existing installation.

Copy `plan.example.json` to a private operator-owned plan and change its paths
to the installed release, native checkouts, environments and existing state.
Every executable and working directory must exist. Each role needs a distinct,
user-owned environment file with mode 0600. Store credential values only in
those private files or the existing runtime-owned secret files. Never put keys
in this repository, plan arguments, model prompts or service descriptions.

The files select the existing profiles: `ZENITH_HOME` for the accounts process;
the original inference identity directory in the inference argv; `HERMES_HOME`,
`ZENITH_HERMES_CHAT_ONLY=1` and the exact compatibility profile ID for Hermes;
`OPENCLAW_STATE_DIR` and `OPENCLAW_CONFIG_PATH` for OpenClaw. Retain the
separate per-runtime inference keys, paired OpenClaw device token and original
owner/MFA bridge authentication. Do not share owner or broker credentials with
unrelated services. Keep tools and messaging delivery disabled until separately
authorized. Configure the optional Zenith OpenClaw provider only after its
native answer checks have passed for the reviewed release.

## Preview, install and start

Run these commands on the selected host as its service user:

```bash
python3 deploy/four_system/services.py render --plan /private/platform-plan.json --directory /private/units-preview
systemd-analyze verify /private/units-preview/*.service /private/units-preview/*.target /private/units-preview/*.timer
python3 deploy/four_system/services.py install --plan /private/platform-plan.json --start
python3 deploy/four_system/services.py status
```

`render` creates files without contacting systemd. The installer uses the user
manager configuration directory: `$XDG_CONFIG_HOME/systemd/user` when configured,
otherwise `~/.config/systemd/user`. Use the same XDG setting as the host user
manager. Every runtime is checked individually; one healthy process cannot
mask another failed service. `install` refuses to
overwrite existing units. With `--start`, it reloads the user manager, enables
the group at boot and requests startup, then checks all six processes are
active. It explicitly reports `readiness_verified: false`; verify authenticated
inference, native runtime health, original login/MFA and the four-system
acceptance separately before treating the deployment as operational.

For services to survive logout and start after reboot, the host administrator
must enable lingering for this dedicated account, for example with
`loginctl enable-linger <service-user>`. Confirm the account and host policy
before doing so. A transient execution workspace is not permanent hosting.

Units restart after unexpected or normal process exit, preserve private umasks,
apply resource caps and refuse privilege escalation. Five rapid failures stop
the restart loop until an operator fixes the cause and resets the failed unit.
These settings are not a sandbox-escape guarantee. Apply host firewall/egress
policy, backups, security updates and storage monitoring separately. Keep APIs
on loopback. Use an authenticated TLS reverse proxy or private tunnel for
remote UI access; do not publish native administrative ports directly.

## Verify operation and recovery

Inspect `systemctl --user status zenith-platform.target` and individual units.
Use `journalctl --user -u zenith-openclaw.service -n 100` for bounded logs;
redact them before sharing. The health timer records failed process-liveness
checks in the journal. External alerts and account sessions are not fabricated.

Run the reviewed pinned-native acceptance against test-owned state and check
the model identity before/after. Verify session persistence and original
account isolation. During a planned maintenance window, test individual
service restart, a host reboot and an extended soak. Reconcile interrupted
native jobs from their receipts; never automatically replay effectful work.
Keep TradingAgents reports under review. No live-order endpoints or broker
credentials are created or enabled by service startup.

## Upgrade and rollback

Archive the current plan, nine generated unit files, reviewed source commit,
model identity receipt and durable state backups. Stop the group with
`systemctl --user disable --now zenith-platform.target`. Move only its generated
unit files to the private archive before installing reviewed replacements.
The installer refuses collisions and rolls back newly created unit files if
writing fails; it never deletes native state or model files.

To roll back, stop the new group, restore the archived units and release paths,
reload the user manager and enable the original target. Keep database backups
and checkpoints intact; no automatic schema downgrade or model reset occurs.
After either upgrade or rollback, repeat readiness and integration checks.

## Tests

```bash
python3 -m unittest discover -s deploy/four_system -v
```

Tests exercise all component connections, strict plans, private credentials,
argument escaping, dependency cycles, no-overwrite behavior, partial-write
recovery, CLI side-effect boundaries and the real `systemd-analyze` parser.
They do not replace actual host restart, reboot, inference or soak tests.
