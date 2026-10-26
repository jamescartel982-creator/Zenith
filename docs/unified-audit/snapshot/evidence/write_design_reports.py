from report_helpers import *
import shutil
# Preserve detailed pinned OpenClaw analysis, clearly contextualized as reused source work.
old=Path('/workspace/openclaw-review-20261025/deliverables/OPENCLAW_REVERSE_ENGINEERING.md').read_text()
put('OPENCLAW_REVERSE_ENGINEERING.md','''# OpenClaw pinned-source analysis for the unified audit

The detailed analysis below is reused from the same immutable source snapshot. Its Zenith main pin is still current. The later unmerged PR19 pilot and Hermes comparison are covered separately in this package. No claim is made that this pin includes later upstream commits or that OpenClaw was executed.

'''+old)
put('ZENITH_CURRENT_ARCHITECTURE.md',f'''# Existing Zenith: main versus preserved development branches

{COMMON}

## Source boundaries

Main is 0.15.0 at `{META['zenith-main']['commit']}`. It contains {META['zenith-main']['tracked_files']} tracked files and {META['zenith-main']['python_modules']} parsed Python modules. PR19 is an unmerged draft at `{META['zenith-pr19']['commit']}`, with {META['zenith-pr19']['tracked_files']} tracked files and {META['zenith-pr19']['python_modules']} Python modules. Original PR18 remains separately preserved at `ac989d869f2c2b961003684dc6ee7843d01d08da`. Nothing from either branch is silently assumed deployed on main.

## Verified trained model and immutable artifacts

{table(['Property','Recorded value'],[
('Base / pinned revision','Qwen/Qwen2.5-0.5B-Instruct / 7ae557604adf67be50417f59c2c2f167def9a775'),
('Architecture','Qwen2ForCausalLM; 24 layers, hidden 896; context ceiling 32768'),
('Parameters','494032768 base; existing rank-8 LoRA adds 4399104; total 498431872'),
('Tokenizer','151665 entries / 151936 embedding vocabulary; original compatibility retained'),
('Base safetensors SHA-256','fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'),
('Adapter SHA-256 / size','7e0701900b40109ee81b3dc097985cda360409006c8b717bda51830f3b6ed85d / 17640136 bytes'),
('Adapter tokenizer.json SHA-256','9c5ae00e602b8860cbd784ba82a8aa14e8feecec692e7076590d014d7b7fdafa'),
('Semantic tokenizer signature','221ea68122dfcfb2772276b69e62fc97ea9b13785ee069b118ee36498b19a418'),
('Format / framework','PEFT LoRA safetensors + pinned base safetensors; PyTorch/Transformers/PEFT'),
('Current quality status','Existing experimental activation retains failed numeric quality/retention gates; not relabeled or promoted')])}

M: The fresh main native smoke loaded this existing checkpoint offline and returned `4` / `Paris` on both direct and routed paths; adapter/profile inventories matched. No training, replacement foundation, adapter merge, data migration or registration occurred. Public model metadata is copied in `evidence/zenith-model-verification.json`; per-file before/after protection checks are exported without private profile hashes.

Sources: {z('agent/providers.py')}, {z('agent/checkpoints.py')}, {z('research_checkpoints/recovery-v1/research.json')}, {z('agent/continual.py')}, {z('agent/deployment.py')}. The separate TinyLM experiment is not the established trained foundation and must not be used as random fallback when a checkpoint is missing.

## Current main owners

{table(['Subsystem','Implemented scope / important limit'],[
('agent/core.py','Bounded text response, context building, one generation lock, complete-turn save; not an autonomous tool loop'),
('agent/providers.py + transport.py','HF/LoRA, Ollama, local server and other existing providers; bounded streaming/cancellation and safetensors/pinned loading'),
('model_registry.py / orchestration.py','Native-first optional registry/routing/federation with account-aware availability, deadlines/retries and reviews; text execution'),
('server.py / web/ / commands.py','Existing FastAPI/SSE account/chat/admin/memory/catalog APIs, plain-JS dashboard and terminal commands'),
('storage.py / personal.py / summaries.py','One SQLite WAL store, account-owned notes/conversations/manual summaries and intentionally shared FTS corpus'),
('execution.py / admin.py / owner_mfa.py','Seven bounded diagnostic capabilities, owner elevation, MFA, grants, narrow network scope and emergency stop; no arbitrary shell'),
('skills.py / skill_access.py','Validated prompt/resource profiles, protected selection and commands; no executable skill learner'),
('continual.py / checkpoints.py / deployment.py','Reviewed CPT/SFT/DPO continuation, replay separation, lineage verification, evaluation/export and explicit rollback; preserve originals'),
('monitoring.py','Bounded account performance metadata; not distributed traces or proof of security'),
('install.py / launchers / Dockerfile','Normal Windows/Linux venv install and CPU-compatible application container; app container is not a tool sandbox')])}

Sources: {z('agent/core.py')}, {z('agent/server.py')}, {z('agent/storage.py')}, {z('agent/personal.py')}, {z('agent/model_registry.py')}, {z('agent/orchestration.py')}, {z('agent/execution.py')}, {z('agent/skills.py')}, {z('agent/monitoring.py')}, {z('install.py')}, {z('Dockerfile')}.

Account passwords are Argon2id. The high-entropy owner code separately uses salted PBKDF2-HMAC-SHA256; TOTP and account/session-bound elevation remain distinct. A global API bearer is not owner identity. Imported shared knowledge must not be mistaken for private account/project retrieval. Legacy positional inserts mean schema changes need additive, versioned tables, not arbitrary new columns on old tables.

## PR19: verified supervised subset, not parity

PR19 adds validated default-off flags, additive platform tables, actor/session/revision checks, metadata HMAC audit, fenced tasks, exact network approvals, bounded HTTP/event replay and one supervised local worker. It executes explicit fixed diagnostic plans, not model-generated autonomous calls. Native queued chat remains local-only by its supported-provider gate. General sandbox, plugins, channels, subagents, project retrieval, browser/computer automation and new UI controls report unavailable.

Sources: {p('agent/runtime.py')}, {p('agent/gateway.py')}, {p('agent/task_store.py')}, {p('agent/permissions.py')}, {p('agent/approvals.py')}, {p('agent/platform_migrations.py')}, {p('docs/platform/benchmark-results.md')}. Its existing schema checksum must remain immutable; later migration versions must be additive.

Earlier evidence at unchanged PR19 head: 277 local tests, one skip; seven Windows/Linux/container jobs and the diagnostic watch passed. Its measured queued path was slower in the recorded CPU smoke. This is existing narrow evidence, not fresh proof of unified/reference-equivalent behavior.

PR18 adds separate bounded reasoning and restricted numeric verification but is also unmerged. File plans flag paths that already exist in PR18, especially planning/verification/config/core/execution, so later implementation cannot overwrite that work accidentally.
''')
put('UNIFIED_INTEGRATION_ARCHITECTURE.md',COMMON+'\n\n'+'''# Proposed unified architecture (P)

## One model identity and one orchestration engine

Extend Zenith's existing Agent/provider/storage/security owners. Do not install OpenClaw and Hermes as two running agents, embed Hermes AIAgent behind a Zenith label, or create a replacement model. The preserved selected checkpoint is the default inference backend. Existing native/provider `generate`/`stream` contracts stay valid; additional structured-turn interfaces are optional and negotiated. A missing/incompatible checkpoint causes a clear unavailable/error result, never random initialization or a hidden model switch.

```mermaid
flowchart TB
  Clients[CLI / web / TUI / companion clients] --> Gateway[Zenith HTTP + WS gateway]
  Channels[Verified channel/device ingress] --> Gateway
  Gateway --> Identity[Account / project / session / live authority]
  Identity --> Runtime[One Zenith task runtime]
  Runtime --> Native[Existing model registry and native inference]
  Runtime --> Supervisor[Specialists and task graph]
  Supervisor --> Runtime
  Runtime --> ToolGate[Typed tool schema / grants / exact approvals]
  ToolGate --> Broker[Isolated execution and egress broker]
  Broker --> Effects[Files / shell / Git / browser / APIs / remote hosts]
  Runtime --> Memory[Scoped memory and context snapshots]
  Runtime --> State[Tasks / events / receipts / outbox / scheduler]
  Memory --> SQLite[Existing Store SQLite owner]
  State --> SQLite
  State --> Learning[Consented trajectories / skill candidates]
  Learning --> Evaluate[Sandbox tests / frozen holdout / review]
  Evaluate --> Activate[Versioned skill activation / rollback]
  Evaluate --> Training[Optional existing continued-training pipeline]
  Training --> Candidate[New immutable candidate checkpoint]
  Candidate --> Review[Retention evaluation / human approval]
```

Inference may run in a separate private service where practical. It mounts original artifacts read-only and exposes a scoped local interface. GPU acceleration/vLLM/quantization remain optional compatibility experiments; CPU inference and the existing tokenizer/adapter stay supported. Extra logical agents do not imply extra foundation models or simultaneous GPU execution. Preserve the current generation lock until a backend's actual concurrency/batching has been measured.

## Native contracts

- `ActorContext`: server-created account/project/session identity, authentication revision and grant references. Never a model-supplied role, raw cookie or owner code.
- `ModelTurn`: text, typed tool proposals, finish reason, provider/source identity and actual usage. Strict schema-constrained local proposals may be explored, but reliability must pass actual selected-model evaluations.
- `ToolSpec`: exact ID/version, schema dialect, effects, target type, required scopes, isolation class, resource limits and output policy. Discovery and dependency availability do not authorize execution.
- `TaskRecord`: goal, step graph, checkpoints, leases/fencing token, budgets, approvals, cancellation and outcome receipts.
- `EvidenceRef`: actual ingested/retrieved source identity/version/hash/excerpt and access scope. A citation must refer to a source retrieved during execution.
- `SkillCandidate`: immutable content/parent hash, type (prompt/workflow/executable package), license/consent provenance, requested capabilities, evaluation and review records.

Model-generated calls are untrusted proposals. Validate schema and immutable argument snapshots, apply current actor/target/grant checks, acquire exact-action approval where needed, persist intent/audit receipt, then dispatch to the broker. Recheck authority after awaited preparation and immediately before effects. Post-call revocation suppresses further use, but cannot undo a completed external action.

## State, sessions and transport

One SQLite owner retains legacy accounts/conversations/memories and adds versioned `platform_*` state. Never copy Hermes state.db/MEMORY.md/USER.md or its jobs.json into production implicitly. Any optional user-authorized import is a separately tested, scoped migration with provenance and backup. Existing shared FTS stays shared; new private documents must never enter it by accident.

Lifecycle expands the PR19 supervised states with preparing, waiting-tool, waiting-approval, blocked-input and child/review phases. Compare-and-swap versions plus expiring worker leases fence old workers. Store queued intent, effect receipts, scoped events and outbox atomically. Crash after possible external acceptance becomes reconciliation, not blind replay or an exactly-once claim. Cancellation propagates to child tasks, streams, workers and scheduled runs with bounded cleanup.

HTTP and WebSocket frames are versioned and bounded. Replayed and live events apply account/project authorization; progress can coalesce, but approval/terminal records persist. Optional OpenClaw RPC and Hermes/ACP/TUI compatibility layers map tested subsets into the same task engine. Their WebSocket/JSON-RPC protocols are not MCP and are not interchangeable by renaming methods.

## Memory and context

Use existing PersonalStore/summaries/turn history as sources; add consented episodic task history, scoped search, derived semantic vectors and project knowledge. Filter authorization before content/ranking. Store confidence/provenance/expiry for inferred memories; user statements, source facts and model inferences remain distinguishable. Deletion purges derived indexes, caches and queued exports; already-produced conversation artifacts have a documented, testable retention policy.

FTS is the initial fallback. Select embeddings only after a pinned licensed model and frozen relevance/resource benchmark justify them. External memory providers require explicit data-egress consent and per-account credentials; provider/profile selection is not permission. Preserve tokenizer context limits and account boundaries during compression.

Hermes-style stable prompt prefixes are an optimization contract, not permission to hide memory changes. Keep immutable per-session system/tool snapshots; put fresh untrusted retrieval/memory in bounded data context. Explicit refresh/compression versions the snapshot and invalidates caches deliberately. Preserve tool-call/result pairs and durable pre-compression evidence; on checkpoint failure do not silently discard history. Measure cache hit/token/latency effects before changing defaults.

## Reviewed learning

Consented successful/failed executions yield redacted trajectories with actual outcomes, tool/argument schemas, versioned environment and usage. Workflow discovery finds reusable structure without copying raw secrets. A native model or deterministic extractor can propose candidates, but cannot activate them or edit production code.

Candidate → isolated tests → independent held-out evaluation → security/license review → human approval → versioned activation. Evaluate workflow success, error recovery, tool correctness, privacy, retained tasks, latency/tokens and rollback. Failures remain failures; human-assisted rescue is scored separately from autonomous success. New skill versions cannot expand live grants. Reference curator defaults or scanners do not waive this gate.

Optional neural training reuses Zenith's existing continued-training and checkpoint owners. Preserve immutable parent hashes, tokenizer compatibility, training-only replay and held-out isolation. Do not train on secrets, private data without consent, or provider outputs without applicable rights. A skill/memory update is not a weight update. A candidate checkpoint requires retention evaluation and explicit approval before reversible deployment.

## Multi-agent and tools

The supervisor configures coding, research, data, infrastructure, cybersecurity, planning, memory, testing, documentation and automation postures. Children receive distinct task/workspace identity, strict-subset permissions, aggregate budgets and cancellation. No implicit administrator/MFA inheritance. Controlled task/evidence/attachment interfaces replace shared ambient global state.

Files/shell/Python/Git/database/infrastructure operations go through the same broker and policy engine. Use isolated worktrees and record changes/tests; never silently commit, push, publish or mutate remote infrastructure. Low-risk reads and high-impact writes have distinct grants. Database/SSH/Docker credentials are scoped handles, not model text. A Docker control capability talks to a privileged broker; workers never receive the host Docker socket.

MCP/plugin/skill metadata is untrusted. Validate bounded manifests, schema/version negotiation, pinned artifact hashes and requested effects before code import. Unknown dependencies or updates require review. Run untrusted executable packages in isolated workers, not the gateway. Prefer native reusable implementations and small attributed ports over importing a second agent core. Passive status/discovery does not install packages or open network connections.

## Channels, automation and media

Every source integration has a separate matrix row and native protocol facet profile. One canonical adapter can support reference-specific variants, but QR/personal WhatsApp and official Cloud API, or WeCom bot versus callback app, stay distinct modes with distinct tests/credentials. Pair verified external account/sender/chat/thread/device identities to Zenith accounts. Reject forged/replayed ingress and protect outbox delivery from duplicate accepted writes. Notifications and scheduled sends require explicit target authority.

Schedules/triggers/heartbeat jobs use durable leases, timezone/DST/misfire/overlap policy and expiring standing service grants. They never convert a login cookie or old MFA elevation into permanent authority. Secrets stay outside model prompts and ordinary logs.

Browser and computer execution require real isolated profiles/VMs, origin-bound vault handles and all-subresource/DNS/redirect/IPv4/IPv6 egress controls. Do not import the owner's host cookies/keychain by default. Human approval binds uploads, downloads, sends, payments and sensitive credential operations to exact targets. Media decoders and OCR/STT/TTS/vision/video workers are bounded and optional; arbitrary encoders do not become compatible with Zenith's tokenizer/embeddings automatically.

## UI, deployment and release boundary

Keep the current logo, chat and installation flow. Add optional task/model/source/permission/memory/candidate/performance controls with clear unavailable states and real model attribution. TUI/desktop/mobile clients are clients of the same engine, not separate agents. Use platform-native code only where needed and verify on actual target OS/device/toolchains.

All new features start disabled. Scope-specific security/E2E and paired behavior/performance tests precede activation. Rollback stops admission, revokes affected grants and drains/fences workers, then disables flags/reverts compatible code while leaving additive data and audit history intact. Never overwrite a checkpoint or restore an older database over newer user changes silently.

No new code implementing this architecture is part of this audit. The exact proposal and blockers are in the file plan and parity report.
''')
put('SOURCE_TO_ZENITH_MAPPING.md',COMMON+'\n\n# Source-to-owner mapping\n\nThe table below covers manually traced core contracts. Every declaration/integration/skill/catalog/doc coverage record is preserved in the full CSV/JSON. A source owner maps to an existing or proposed Zenith owner, not to an imported second agent.\n\n'+table(['ID / reference','Behavior','Exact source owners','Existing main / PR19','Proposed group'],[(r['id']+' / '+r['reference_project'],r['feature_name'],'; '.join(s['path'] for s in r['sources']),r['zenith_main_equivalent']+' / '+r['zenith_pr19_equivalent'],r['group']) for r in ROWS if r['entry_type']=='core_behavior'])+'\n\nSpecific channel/provider identities share canonical owners only when protocol behavior is compatible. Source-specific modes and acceptance facets remain separate. File-plan records flag overlaps with the still-unmerged PR18 and PR19; reconciliation is required before editing.\n')
(E/'design-source-citations.json').write_text(json.dumps(CITATIONS,indent=2)+'\n')
