# Security hardening — 0.17.5

This is a defensive source review and local adversarial test of Zenith at
baseline `8c28d2b8f3e2f47da1ab448de85bcb0c435d89c3`. Tests use isolated databases,
ephemeral credentials and loopback servers. No external system was attacked.
It is not a certification that every vulnerability has been found.

## Findings and implementation

| Source-backed finding | Fix and destination | Executable verification |
| --- | --- | --- |
| Raw server access key lived in browser sessionStorage and the input field. | `agent/browser_access.py`, `agent/server.py`, `agent/web/app.js`: exchange it for a signed, host-only HttpOnly grant; clear input and legacy storage. Explicit disconnect revokes the account session. | Tamper, expiry, key rotation, cookie attributes, reload, disconnect and native Bearer tests. |
| Early Origin rejections and unhandled failures could omit security headers. | `agent/http_security.py`: ASGI send wrapper covers normal/error responses; strict Origin/Host checks, CSP, no-store, MIME, frame, permissions and cross-origin policies. HSTS uses trusted HTTPS scheme only. | HTTP status matrix 200/400/401/403/404/422/500; HTTP/HTTPS variants; actual Chromium inline-script block. |
| Exceptions could expose upstream details in app logs; discovery query URLs could carry keys. | Fixed error messages, sanitized JSON and validation errors; default CLI Uvicorn access logs disabled. `agent/discovery.py` rejects configured keys before making requests. | Canary key in exceptions and discovery parameters never reaches responses, captured app logs or the mocked transport. |
| Main chat lacked general credential filtering, including split streaming chunks and persisted traces. | `agent/redaction.py`, `core.py`, `storage.py`, `personal.py`, `skill_catalog.py`, `summaries.py`: known literal/pattern filtering before context, output and writes; persistent credential inputs rejected. | Character-sized chunks, every tested boundary, bounded-buffer failure, legacy history summarization and transactional instruction-pack rollback. |
| Browser account changes could race delayed privileged replies. | `agent/web/app.js`: account and authority epochs discard stale fetch/stream results; privileged views clear on lock or account change. | Real owner response held in transit, account switched, then response released and rejected. |
| Public quickstart and login page published owner bootstrap instructions; OpenAPI still advertised routes. | `README.md`, `agent/web/index.html`, `server.py`: remove public instructions and disable schema exposure. New owner-help route requires server access, configured owner login and current owner elevation. | Locked owner and other accounts denied; unlocked owner succeeds; public quickstart/page assertions and schema 404. |
| Existing MFA key reads followed symlinks and left permissive mode bits. Configuration overwrites were not atomic/private from creation. | `agent/private_files.py`, `owner_mfa.py`, `setup.py`: bounded regular owner-file reads, no-follow where available, POSIX 0600; mkstemp and atomic replacement for configuration. | Symlink denial, mode tightening, failure before replace preserves old bytes and cleans temporary files. |
| Database relied on existing file/account isolation without explicit secure-delete/defensive connection settings. | `agent/storage.py`: enable both where supported; preserve SQL parameter binding and private-file checks. | SQL-like login input, cross-account history denial, SQLite settings, FTS add/search/delete and unchanged normal data verification. |

The browser renderer continues to build text nodes rather than HTML. Links now
allow only bounded HTTP(S) URLs without embedded credentials/control characters.
Real Chromium tests supply HTML, SVG, event handlers, JavaScript links and a
malicious stored display name. All stayed inert. CSP is additional protection,
not a substitute for safe rendering.

Review regressions additionally verify punctuation-bearing passwords across
stream boundaries and removal of private sidebar conversation titles on
disconnect. Login acceptance waits for actual skill hydration, and source text
checks read UTF-8 explicitly on Windows.

## Authentication and owner boundaries

The browser grant authorizes entry through a configured server gate; it does not
grant owner privileges. Account sessions, configured owner identity, hashed owner
code, MFA policy, capability grants, target scope, quotas and emergency stop
remain server-side. Model output cannot change these permissions. Restricted
execution stays disabled by default.

Grants expire after one hour and rotate with the server access key. Disconnect
clears the browser copy and revokes its account session. A separately stolen
stateless access grant can still pass the server gate until expiry/key rotation;
it does not recover the user's separately revoked account session. HTTPS is
required for remote use; loopback HTTP intentionally has no Secure/HSTS flag.

Only an elevated configured owner can read the new in-app owner command
reference. Source code, operator documentation and old Git history remain public.
Knowing a command name grants no privilege. The unchanged local profile checked
here has **no owner configured**, so nobody has owner access there yet. Ownership
must be bootstrapped privately by the trusted server operator; the update does
not guess an owner from GitHub identity or issue a shared password.

## Measurements and reproducibility

Baseline: 390 root tests, one skipped, passed in 67.673 seconds. Post-change
counts and durations are recorded in the adjacent validation report. Test-suite
duration is not an inference speed benchmark.

```bash
python -m unittest discover -s tests -q
python -m unittest discover -s integrations/runtime_bridge/tests -q
python -m unittest discover -s integrations/inference_service/tests -q
python -m unittest discover -s integrations/trading_service/tests -q
python -m scripts.security_browser_acceptance --output /tmp/security-browser.json
```

Use an isolated `ZENITH_HOME` for tests. The browser script requires the optional
test-only Playwright SDK and Chromium; CI pins Playwright 1.64.1. Integration
packages must be installed in their documented environments or put on
`PYTHONPATH`. Model acceptance additionally uses the frozen local identity:

```bash
python -m scripts.smoke_personalized_model --identity /path/to/identity.json \
  --generated-recipes --output /tmp/security-model.json
```

Reports in [benchmarks/security-hardening](benchmarks/security-hardening) contain
only fixture results and preservation metadata, never database contents or
credentials. Actual preserved-model inference returned `Bonjour` for the saved
French preference and `4` for the generated coding-recipe task. Tensor and
checkpoint identity hashes remained unchanged. This verifies those tasks, not
general intelligence or universal accuracy.

Normal local-state checks preserved all 31 existing table contents, configuration
bytes and the generated recipe installation. Database integrity passed. POSIX
directory/config/DB/sidecar modes were already 0700/0600; no account data was
rewritten. A private local SQLite backup was created before opening the updated
store. A bounded scan found no configured literal key in the scanned tracked
text files; it does not establish that Git history contains no unknown secret.

## Migration and rollback

No model migration, training, tokenizer conversion or credential import occurs.
Browser grants use no new database tables. Supported SQLite connection settings
take effect on the next process start. Re-enter the server access key once after
upgrading because old browser storage is intentionally cleared. Native Bearer
clients keep working. New metadata uses the same existing SQLite database.

Stop the server before upgrade/restore; retain a private environment and SQLite
backup. Upgrade the existing installation and restart all workers. The source
manifest is rebuilt with the release. Existing independently installed bridge
and inference packages must be updated to their matching 0.17.5 Zenith pin.

To roll back, restore the prior reviewed application/environment and restart;
no downgrade schema migration is needed for these changes. Restoring an older
database can lose subsequent user data. Reverting this patch reintroduces the
listed exposures: prefer correcting a regression without removing protections.
Never publish state backups, enrollment keys, owner codes or model weights.

## Residual risks and operating requirements

- SQLite remains plaintext. Secure deletion does not guarantee erasure from
  WAL/FTS, storage snapshots or backups. Use OS encryption, private encrypted
  backups and NTFS ACLs on Windows. A compromised OS account or Docker daemon
  can bypass application controls.
- Filtering is best effort: supported credential patterns and configured exact
  literals of at least eight characters, not arbitrary encodings or unknown
  formats. Ambiguous streaming tails are buffered, capped at 16 KiB and fail
  closed; chunk boundaries can change. Ordinary safe output is released promptly.
- Existing databases, logs and Git history are not silently rewritten. Rotate
  previously exposed keys and investigate/remove old copies separately.
- MFA enrollment deliberately returns its one-time secret to the authenticated,
  reauthenticated owner over the protected no-store route. This is necessary to
  enroll an authenticator; do not put enrollment material in model prompts.
- Configure proxy/SDK/upstream logs separately. Default application request logs
  omit URLs, but external software can still log them. Never put keys in URLs.
- Keep loopback binding, explicit allowed hosts, HTTPS for remote access, firewall,
  dependency scanning, scoped grants and reviewed isolated execution. No public
  host, live trading, additional network permission or unrestricted tool was enabled.
- The browser checks use an explicitly labeled fixture model. Integration tests
  verify local contracts; they do not establish full real upstream-service parity
  or resistance to every browser, prompt injection or sandbox attack.
