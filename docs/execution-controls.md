# Owner authentication and restricted execution

Model knowledge cannot be reliably disabled with an administrator code. Zenith enforces permissions on execution, network access, and sensitive workflows. Conversation profiles remain instructions, rather than neural access-control boundaries.

## Authentication and MFA

Account passwords use Argon2id with independent salts, 19 MiB memory, two iterations, and one lane. Existing PBKDF2 accounts retain access and migrate on successful login. Before a production application upgrade, take a consistent SQLite backup and preserve the MFA key with it. Older application versions cannot read Argon2id hashes: a software downgrade requires a compatible database backup, while model rollback can keep the upgraded application and restore only its previous model settings. The separate high-entropy local owner code keeps its existing hashed recovery/bootstrap mechanism. Only the account configured in `admin_owner` is the owner; a model response or a forged request field cannot create that role.

Sign in, open Admin, and unlock with the local owner code. In **Owner multifactor authentication**, confirm the account password, store the displayed secret in a standard TOTP authenticator, and confirm its six-digit code. Enrollment expires after ten minutes. The setup secret is cleared from the UI after confirmation; known enrollment secrets are rejected in model prompts and saved memories.

After enrollment, owner elevation also requires the authenticator code. Codes are single-use across the accepted time window, including concurrent requests. Secrets are encrypted with Fernet; the encryption key is in `owner-mfa.key` beside the database, created with owner-only POSIX file permissions. Windows access depends on the account's file ACLs. Back up the database and key together. The server necessarily has access to both to verify TOTP; this is not hardware-backed secret storage. Sessions expire and are bound to the real signed-in account/token. Lock, logout, and owner-code rotation revoke restricted grants and MFA session state.

From the trusted OS-owner terminal, deliberate recovery is available:

```text
zenith admin reset-mfa --username YOUR_USERNAME --confirm-reset
zenith admin stop-tools --username YOUR_USERNAME
```

A reset revokes elevations and capability grants; the owner must enroll again before restricted tools can run. Local recovery trusts operating-system access, as the existing owner bootstrap does. It does not grant remote recovery based on a username alone.

## Explicit capabilities and scopes

All capability grants begin disabled, including for the owner. After MFA verification, activate an individual capability for a short period. Grants are tied to the login token and expire no later than owner elevation. Resuming after a stop restores no grants.

- Offline capabilities: bounded calculator, SHA-256, Base64 decoding, pasted-code heuristic audit, and URL component inspection. Scope is exactly `{"kind":"offline"}`.
- Network capabilities: one TCP connection or one TLS certificate verification. There is no shell, exploit runner, port sweep, credential attack, malware execution, or destructive action.

Network scope records explicit narrow CIDRs, allowed ports, and a written-authorization reference. For example, an **owned lab fixture**, with its actual approved port:

```json
{"kind":"network","cidrs":["127.0.0.1/32"],"ports":[8443],"authorization_reference":"Owned local test service"}
```

Targets must be explicitly approved literal IP addresses. Hostname lookup is intentionally disabled so an untrusted plan cannot send data through an out-of-scope DNS query. The server validates the numeric address before connecting. Out-of-scope, link-local, multicast, and unspecified addresses are rejected. Redirects are not followed. Scope declarations require the owner to have real authorization; Zenith does not independently prove third-party ownership from a typed reference. Connect/TLS operations use bounded socket timeouts. TLS verification uses the supplied IP identity, so the peer certificate must cover that IP.

The old pasted-code/URL endpoint uses the same capability enforcement, preventing a legacy-route bypass. Its benign offline utility controls retain their existing owner workspace flow. Emergency stop disables the owner tool workspace and all restricted execution paths. It blocks subsequent operations and discards results when revocation is observed during a bounded operation; it is not an instantaneous OS kill of an in-flight socket operation.

## API and bounded plans

All routes retain the server-access gate, signed-in owner requirement, and cross-origin protections. No model-generated permission fields are trusted.

| Route | Behavior |
| --- | --- |
| `POST /api/admin/mfa/setup` | Password reauthentication and pending TOTP setup |
| `POST /api/admin/mfa/confirm` | Confirm a single-use enrollment code |
| `GET /api/admin/execution` | Inspect active grants and emergency state |
| `POST /api/admin/execution/grant` | Explicit capability, scope, and expiry |
| `DELETE /api/admin/execution/grants` | Revoke this login's grants |
| `POST /api/admin/execution/stop` | Persistent emergency shutdown and grant revocation |
| `POST /api/admin/execution/resume` | MFA-verified explicit resume; grants remain disabled |
| `POST /api/admin/execution/run` | Validate and execute a scoped diagnostic |
| `POST /api/admin/execution/plan` | Execute a supplied plan with at most eight steps and a time budget |
| `GET /api/admin/execution/history` | Owner activity events and task status |

A plan uses explicit `tool`/`arguments` objects. Each step checks current permissions and stops on failure, expiry, revocation, or emergency shutdown. Task history stores status, tool IDs, and completed-step counts, excluding pasted source and full results. It supports inspection of progress, rather than automatic resumption of arbitrary commands. The model's trained ability to suggest a plan does not make its plan authorized.

SQLite activity records include grants, execution outcomes, denial/failure events, target identifiers for network diagnostics, and emergency actions. They avoid pasted inputs and credentials. They are local operational logs, not immutable or independently tamper-proof audit storage; the OS operator controls the database. HTTP authentication denials also appear in normal server access logs.

## Memory remains external

Existing memories and retrieval remain in place. The Memory dialog can explicitly save or forget an account-owned conversation summary. Summaries are bounded, labeled as untrusted task context, and deleted with their conversation. They do not update weights. Summarization shares the normal generation lock and retains account/conversation isolation. Long-context architecture limits are preserved; the current CPU training pilot does not establish long-context reasoning improvement.
