# Security hardening verification — 2026-10-26

Baseline source: `68b82b5a2c8783657a0e4740d79ec30d99625c99`.
Changes target HTTP trust boundaries, private local storage and dependency
advisories. No upstream Hermes/OpenClaw code, model weights, adapter lineage,
tokenizer files, training data, production profile or account data was replaced.

## Concrete findings and fixes

- Previously, arbitrary Host names reached the default unauthenticated loopback
  API, leaving a DNS-rebinding boundary open. Host names are now explicit,
  loopback-only by default; remote names require both configuration and a
  server token of at least 32 characters. IPv4/IPv6 loopback access is tested.
- Model/request field limits previously ran after body buffering and JSON
  parsing. A 512 KiB total cap now applies before routing, even without a
  Content-Length, with a 15-second body deadline and ambiguous-length rejection.
- Browser cross-site API requests without Origin are now rejected using fetch
  metadata. Existing same-origin write checks remain in place.
- Default framework validation responses echoed rejected inputs. Responses now
  retain field locations and messages while removing inputs and context.
- SQLite inherited permissive creation modes. New databases/directories are
  private; POSIX database/WAL/SHM group/other access is removed, and unsafe
  ownership, symlinks and group/world-writable data directories are rejected.
- The original installed dependency scan identified 18 advisories across five
  packages. Security floors now require cryptography >=50.0.2,<51, Transformers
  >=5.10.4,<5.11, datasets >=5.0.1,<6 and fsspec >=2026.6.0,<2027. PEFT's floor
  is 0.18.1. Requests/urllib3 floors are also raised. The normal installer
  upgrades pip; the tested compatibility environment uses pip 26.2.

## Actual local checks

- Complete suite on the patched compatibility environment: **334 tests run,
  333 passed, one skipped, 44.231 seconds**.
- Thirteen initial focused HTTP/private-storage tests passed, followed by the
  additional writable-directory regression in the complete suite.
- A real Uvicorn process and loopback HTTP connections passed UI/health checks,
  rejected hostile Host and cross-site requests, redacted invalid passwords,
  and rejected a chunked body larger than the cap.
- The original Qwen2.5-0.5B base revision plus selected Zenith adapter loaded
  with Transformers 5.10.4 and PEFT 0.18.1. Direct and streaming generation both
  returned `4` to the fixed arithmetic prompt, and supervised training-example
  preparation passed. This is compatibility evidence, not a quality benchmark.
- `pip check` in the compatibility environment: no broken requirements.
- Patched dependency scan: **95 selected installed distributions, zero known
  advisories**, with no advisory exclusions. The count includes audit tooling;
  the original scan covered 75 distributions. Raw before/after reports are
  included. Zenith's own project is excluded from the public-package lookup;
  its source is tested and reviewed separately.
- Base weights, adapter weights and adapter tokenizer hashes were rechecked
  against their previously recorded values; see `model-preservation.json`.

The compatibility environment overlays updated packages on read-only access to
the original installed dependencies, avoiding a second large Torch download.
Python's `pip check` sees those inherited distributions; `uv pip check` does not
follow that `.pth` overlay and reports them absent. Fresh independently resolved
Windows/Linux installation and dependency audits run in CI before merge.

## Migration, rollback and limits

Read [SECURITY.md](../../../SECURITY.md) before upgrading a public deployment.
Add the exact domain to `ZENITH_ALLOWED_HOSTS`, retain the private server token,
and keep the backend behind authenticated HTTPS or a private VPN. Old volumes
may need corrected ownership/permissions; choose a dedicated private folder.
No Windows NTFS ACL automation or host-firewall changes are performed here.

Back up the current environment and private data before installation. To roll
back application code, return to the baseline revision and its prior environment;
database schemas/content and checkpoint formats remain compatible. Tightened
file permissions remain in place. Rolling back dependencies reintroduces their
recorded advisories and is a recovery step, not a secure long-term deployment.

This audit does not certify the OS, reverse proxy, GPU stack, external runtimes,
unreviewed plugins, backups or an unknown deployed server. It does not establish
universal prompt-injection resistance, sandbox escape immunity, DDoS protection
or that the project is unhackable. Continue reviewing advisories and updates.
