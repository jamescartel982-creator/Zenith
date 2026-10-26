# Deployment, migrations and rollback proposal

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Preserve installation and data

Keep the existing clone → install.py → run.ps1/run.sh workflow and Python-only text path. No mandatory Node26, GPU, Docker daemon, browser, messaging credential or new large model download may be added to basic local installation. The current Zenith Python requirement and public APIs stay intact; optional workers can have separately pinned runtimes. Verify Linux, Windows, CPU and existing container paths in CI. Core orchestration must not import Hermes or launch OpenClaw as a replacement engine.

Use a single authoritative existing SQLite store for accounts/conversations and additive task/memory/workflow tables where compatible. PR19 migration V1 checksums remain immutable; add a new version with transactional upgrade, read/write compatibility and migration tests. Do not edit user databases during this audit. Back up with SQLite's backup API or a stopped/WAL-consistent procedure, encrypt sensitive backups and preserve access permissions. Record schema version, row counts and source hashes, never export private conversation content into public benchmark files.

## Release sequence

1. Obtain expanded-audit approval and choose the reviewed base. Snapshot code SHA, immutable model/adapter/tokenizer hashes and private configuration/data backup. Resolve PR18/19 overlaps explicitly.
2. Install pinned optional dependencies in separate environments; resolve licenses/SBOM and native wheels for each supported OS. Run existing regression and default-off import/installation tests.
3. Apply additive migrations in a test copy, test old writers and rollback behavior, then migrate the intended local environment with effects disabled.
4. Validate actor/MFA/grant paths, secret broker, sandbox/egress and emergency shutdown before registering any effectful tool. Gateway binds local/closed by default; external exposure needs TLS/proxy/origin/rate-limit/security acceptance.
5. Run actual selected Zenith inference and first bounded tool task, then per-subsystem tests. Only connect real services under the intended account's explicit scoped authorization; credentials stay local or in an approved vault.
6. Enable one feature flag/account at a time with short-lived grants and quotas. Monitor task failures, denied effects, audit durability and latency; publish measured evidence and unresolved blockers. Code publication/deployment remains separately reviewable.

## Rollback

Deny admissions; revoke/rotate affected grants and cancel/fence workers; reconcile uncertain external writes; drain or explicitly abort scheduled/outbox work; disable the capability flag. Preserve task receipts, user history and additive tables. Return to the previous reviewed application version only if compatibility tests show it can read/write the migrated schema; otherwise use a reviewed forward repair. Never restore an old DB over newer user writes. A point-in-time restore is a deliberate recovery requiring preserved newer data and reconciliation.

Model rollback uses existing checkpoint/deployment owners and immutable lineage. Do not delete or overwrite the original model or adapter. This integration plan does not activate candidates, retrain or merge adapters. Any later learning experiment exports a separate candidate, verifies hashes/tokenizer/retention/security gates and requests promotion review. Failed experimental quality gates remain recorded.

## Platform boundaries

Linux/CPU and existing supported Windows launch paths are first-class. Rootless/container/VM isolation must be available before shell execution; missing isolation means disabled, never host fallback. NVIDIA/CUDA, vLLM, local media and accelerated embeddings are optional and benchmark-gated. macOS/iOS companion permissions/signing and Android hardware/Termux variants require actual devices and upstream license review; Linux/Windows desktop packaging must be validated independently. Cloud/remote deployments require owned service accounts, pinned SSH identities, network controls, TLS and data-retention policy. No current test establishes these new platform integrations.
