# Security

Zenith uses server-side account/owner permissions, Argon2id password hashing,
expiring sessions, owner TOTP MFA, scoped execution grants, an emergency stop,
and optional offline container execution. Model text cannot grant permissions.
These protections reduce risk; they are not a guarantee against compromise.

The [0.17.5 security report](docs/security-hardening.md) records the source audit,
local adversarial tests, real-browser checks and unchanged-model verification.
The public README and login page no longer publish owner command instructions.
The command reference in the owner workspace requires a signed-in configured
owner with current server-side elevation. Public source and Git history remain
readable; command names are not secrets or authentication factors.

## Run privately

Keep the default `127.0.0.1` binding. Do not forward port 7860 directly to the
internet. For remote access, use an authenticated HTTPS reverse proxy or a
private VPN, firewall the backend from other clients, and configure a random
`ZENITH_API_TOKEN` of at least 32 characters. Never put that token in a URL,
prompt, screenshot, public repository or shared log. Configure owner MFA before
granting execution permissions; restricted tools remain disabled by default.

Starting with 0.17.3, only `localhost`, `127.0.0.1` and `[::1]` Host headers are
accepted by default. Public domains and LAN IP addresses must be listed
explicitly in `ZENITH_ALLOWED_HOSTS`, for example:

```dotenv
ZENITH_ALLOWED_HOSTS=localhost,127.0.0.1,::1,chat.example.com
```

Non-loopback entries require a strong server token. Entries are host names or
IP addresses, without schemes, ports or wildcards. Configure your proxy to
preserve the intended Host and set forwarding headers itself; never trust
forwarded headers from arbitrary internet peers. Existing public deployments
must add their real hostname before upgrading. Loopback installs need no change.

Requests have a 512 KiB total body cap, including chunked bodies, and a
15-second body-read timeout before JSON parsing. Rejected validation inputs are
not echoed. Browser-reported cross-site API requests are rejected in addition
to same-origin checks on writes. Put connection limits, request-rate limits
and TLS termination at the proxy for public deployments; app limits do not
protect against volumetric DDoS or a compromised host.

Version 0.17.5 replaces browser `sessionStorage` API keys with host-only HttpOnly,
SameSite=Strict grants that expire after one hour; HTTPS adds Secure. Re-enter
the access key once after upgrading. Disconnect clears browser access and revokes
that account session; rotating the server key revokes all browser access grants.
Native Bearer authentication remains supported. Use HTTPS for remote clients.

App HTTP responses, including rejected requests and handled internal errors,
get a restrictive same-origin CSP, no-store, nosniff, clickjacking protection,
no-referrer, cross-origin policies and permissions headers. HSTS is emitted only
when the trusted ASGI scheme is HTTPS. No third-party browser scripts are needed.
Configured literal keys and common credential formats are filtered before chat
delivery/persistence; this cannot detect every unknown or encoded secret. CLI
server access logs omit request URLs by default. Configure proxy, SDK and service
logs separately and rotate any credentials already exposed in old logs or data.

## Protect local state and tools

Run Zenith as an ordinary dedicated OS account. On POSIX, new data directories
use mode 0700, and the database and existing WAL/SHM sidecars are restricted to
owner read/write bits. Database symlinks, non-regular files and databases owned
by a different UID are rejected. Group/world-writable data directories are
rejected rather than changing permissions on a possibly shared folder. This may require fixing ownership on an old
Docker volume or configuring the real private directory instead of a symlink.
Existing database contents and schemas are preserved. Existing parent-directory
permissions are not changed automatically. On Windows, restrict the data/profile
directory using NTFS ACLs; POSIX mode bits do not implement Windows account ACLs.

SQLite connections enable secure deletion and, where supported by Python/SQLite,
defensive mode. These settings do not encrypt the database or guarantee removal
from WAL pages, FTS indexes, snapshots or backups. Use OS disk encryption and
private encrypted backups. New configuration files are written through private
temporary files and atomically replaced; existing configuration bytes are kept.

Keep encrypted MFA material and its local key private. Back up the data/profile
directory to encrypted, access-controlled storage and test restoration. Backups,
exported chats, training files and logs need their own access controls. Anyone
who controls the OS account or Docker daemon can bypass application controls.

Keep execution grants short-lived and target-specific. Use only reviewed local
container images, never mount the Docker socket or host credentials into a
model-controlled runtime, and keep sandbox execution off unless needed.
Treat model output, retrieved documents, MCP results and third-party skills as
untrusted input. Do not enable unreviewed plugins or arbitrary remote model code.
Keep native Hermes/OpenClaw profiles, environments and service credentials
separate; installing their prerequisites does not secure or deploy those agents.

## Updates and verification

Use the current main branch and rerun the existing installer in the same virtual
environment to upgrade dependencies while preserving configuration and data.
Version 0.17.3 raises security floors for cryptography, Transformers, datasets
and fsspec. Transformers 5.10 changes chat-template return defaults, so Zenith
now requests the original list/tensor format explicitly. Weights, tokenizer
files and adapter lineage are not converted or retrained.

Run `zenith verify --json` for installed-file consistency and
`zenith verify --source . --json` for a source checkout. These are consistency
checks, not cryptographic publisher signatures or malware scans. Dependency
advisories evolve: review automated update PRs, run security scans, and retain
an installation/environment backup before dependency upgrades.

Report suspected vulnerabilities privately to the repository owner. If GitHub
private vulnerability reporting is enabled, use the repository's Security tab.
Do not post credentials, user databases or exploit details in public issues.
For a suspected live compromise, disconnect external access, stop tool workers,
use the emergency stop, revoke affected sessions/credentials from a trusted
machine, and restore reviewed code and state after investigating the host.
