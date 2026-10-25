# Existing Zenith: main versus preserved development branches

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

## Source boundaries

Main is 0.15.0 at `e6963d9c6f45c196ae2e301819ae1ae093b35c41`. It contains 375 tracked files and 128 parsed Python modules. PR19 is an unmerged draft at `44d55d23cb946254a4a718a35a7c5432003cc01b`, with 426 tracked files and 148 Python modules. Original PR18 remains separately preserved at `ac989d869f2c2b961003684dc6ee7843d01d08da`. Nothing from either branch is silently assumed deployed on main.

## Verified trained model and immutable artifacts

| Property | Recorded value |
| --- | --- |
| Base / pinned revision | Qwen/Qwen2.5-0.5B-Instruct / 7ae557604adf67be50417f59c2c2f167def9a775 |
| Architecture | Qwen2ForCausalLM; 24 layers, hidden 896; context ceiling 32768 |
| Parameters | 494032768 base; existing rank-8 LoRA adds 4399104; total 498431872 |
| Tokenizer | 151665 entries / 151936 embedding vocabulary; original compatibility retained |
| Base safetensors SHA-256 | fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe |
| Adapter SHA-256 / size | 7e0701900b40109ee81b3dc097985cda360409006c8b717bda51830f3b6ed85d / 17640136 bytes |
| Adapter tokenizer.json SHA-256 | 9c5ae00e602b8860cbd784ba82a8aa14e8feecec692e7076590d014d7b7fdafa |
| Semantic tokenizer signature | 221ea68122dfcfb2772276b69e62fc97ea9b13785ee069b118ee36498b19a418 |
| Format / framework | PEFT LoRA safetensors + pinned base safetensors; PyTorch/Transformers/PEFT |
| Current quality status | Existing experimental activation retains failed numeric quality/retention gates; not relabeled or promoted |

M: The fresh main native smoke loaded this existing checkpoint offline and returned `4` / `Paris` on both direct and routed paths; adapter/profile inventories matched. No training, replacement foundation, adapter merge, data migration or registration occurred. Public model metadata is copied in `evidence/zenith-model-verification.json`; per-file before/after protection checks are exported without private profile hashes.

Sources: [agent/providers.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/providers.py#L1), [agent/checkpoints.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/checkpoints.py#L1), [research_checkpoints/recovery-v1/research.json:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/research_checkpoints/recovery-v1/research.json#L1), [agent/continual.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/continual.py#L1), [agent/deployment.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/deployment.py#L1). The separate TinyLM experiment is not the established trained foundation and must not be used as random fallback when a checkpoint is missing.

## Current main owners

| Subsystem | Implemented scope / important limit |
| --- | --- |
| agent/core.py | Bounded text response, context building, one generation lock, complete-turn save; not an autonomous tool loop |
| agent/providers.py + transport.py | HF/LoRA, Ollama, local server and other existing providers; bounded streaming/cancellation and safetensors/pinned loading |
| model_registry.py / orchestration.py | Native-first optional registry/routing/federation with account-aware availability, deadlines/retries and reviews; text execution |
| server.py / web/ / commands.py | Existing FastAPI/SSE account/chat/admin/memory/catalog APIs, plain-JS dashboard and terminal commands |
| storage.py / personal.py / summaries.py | One SQLite WAL store, account-owned notes/conversations/manual summaries and intentionally shared FTS corpus |
| execution.py / admin.py / owner_mfa.py | Seven bounded diagnostic capabilities, owner elevation, MFA, grants, narrow network scope and emergency stop; no arbitrary shell |
| skills.py / skill_access.py | Validated prompt/resource profiles, protected selection and commands; no executable skill learner |
| continual.py / checkpoints.py / deployment.py | Reviewed CPT/SFT/DPO continuation, replay separation, lineage verification, evaluation/export and explicit rollback; preserve originals |
| monitoring.py | Bounded account performance metadata; not distributed traces or proof of security |
| install.py / launchers / Dockerfile | Normal Windows/Linux venv install and CPU-compatible application container; app container is not a tool sandbox |

Sources: [agent/core.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/core.py#L1), [agent/server.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/server.py#L1), [agent/storage.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/storage.py#L1), [agent/personal.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/personal.py#L1), [agent/model_registry.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/model_registry.py#L1), [agent/orchestration.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/orchestration.py#L1), [agent/execution.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/execution.py#L1), [agent/skills.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/skills.py#L1), [agent/monitoring.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/agent/monitoring.py#L1), [install.py:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/install.py#L1), [Dockerfile:1](https://github.com/jamescartel982-creator/Zenith/blob/e6963d9c6f45c196ae2e301819ae1ae093b35c41/Dockerfile#L1).

Account passwords are Argon2id. The high-entropy owner code separately uses salted PBKDF2-HMAC-SHA256; TOTP and account/session-bound elevation remain distinct. A global API bearer is not owner identity. Imported shared knowledge must not be mistaken for private account/project retrieval. Legacy positional inserts mean schema changes need additive, versioned tables, not arbitrary new columns on old tables.

## PR19: verified supervised subset, not parity

PR19 adds validated default-off flags, additive platform tables, actor/session/revision checks, metadata HMAC audit, fenced tasks, exact network approvals, bounded HTTP/event replay and one supervised local worker. It executes explicit fixed diagnostic plans, not model-generated autonomous calls. Native queued chat remains local-only by its supported-provider gate. General sandbox, plugins, channels, subagents, project retrieval, browser/computer automation and new UI controls report unavailable.

Sources: [agent/runtime.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/runtime.py#L1), [agent/gateway.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/gateway.py#L1), [agent/task_store.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/task_store.py#L1), [agent/permissions.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/permissions.py#L1), [agent/approvals.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/approvals.py#L1), [agent/platform_migrations.py:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/agent/platform_migrations.py#L1), [docs/platform/benchmark-results.md:1](https://github.com/jamescartel982-creator/Zenith/blob/44d55d23cb946254a4a718a35a7c5432003cc01b/docs/platform/benchmark-results.md#L1). Its existing schema checksum must remain immutable; later migration versions must be additive.

Earlier evidence at unchanged PR19 head: 277 local tests, one skip; seven Windows/Linux/container jobs and the diagnostic watch passed. Its measured queued path was slower in the recorded CPU smoke. This is existing narrow evidence, not fresh proof of unified/reference-equivalent behavior.

PR18 adds separate bounded reasoning and restricted numeric verification but is also unmerged. File plans flag paths that already exist in PR18, especially planning/verification/config/core/execution, so later implementation cannot overwrite that work accidentally.
