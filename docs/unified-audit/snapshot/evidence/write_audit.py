from report_helpers import *
import platform,sys,shutil,subprocess
put('REPOSITORY_AUDIT.md',f'''# Pinned-source architecture audit

{COMMON}

## Review boundary and preservation

The latest mission expands the approved OpenClaw-only scope to Hermes. Its Phase 1 explicitly says not to modify Zenith before this audit is completed and approved. Previous blanket approvals and the separate OpenClaw pilot do not override that new boundary. No application code, README, deployment, model, active profile, checkpoint registration or PR state was changed for this audit.

The existing OpenClaw clone was reused at its verified immutable commit; Hermes and current Zenith main were freshly cloned. OpenClaw's pin is the same snapshot as the earlier source audit, not a claim to include every subsequent upstream commit. Main branches can move: acceptance must name exact reference commits and include a delta audit before later pin upgrades. The code inventory hashes every tracked file in all four views. Manual semantic tracing covers critical owners; whole-tree hashing/import indexing is **not** line-by-line manual review or a complete resolved call graph.

{table(['View','Commit / branch','Tracked files','Python AST modules','Runtime / license'],[
('OpenClaw',META['openclaw']['commit']+' / '+META['openclaw']['branch'],META['openclaw']['tracked_files'],META['openclaw']['python_modules'],'2026.10.7; Node >=24.22.1 <25 or >=26.12.1; pnpm 12.15.0; MIT'),
('Hermes',META['hermes']['commit']+' / main',META['hermes']['tracked_files'],META['hermes']['python_modules'],'Package version 0.0.0; PM Python 3.14; Node >=26; MIT, Nous Research 2025'),
('Zenith main',META['zenith-main']['commit']+' / main',META['zenith-main']['tracked_files'],META['zenith-main']['python_modules'],'0.15.0; Python >=3.10; Windows/Linux CI 3.10/3.12; Apache-2.0'),
('Zenith PR19',META['zenith-pr19']['commit']+' / feature/openclaw-platform',META['zenith-pr19']['tracked_files'],META['zenith-pr19']['python_modules'],'Unmerged draft supervised task pilot; same trained model and installer')])}

The original development checkout is separately preserved at PR #18 commit `ac989d869f2c2b961003684dc6ee7843d01d08da` (optional reasoning). PR #18 and PR #19 remain open/unmerged; their overlapping config/core/execution/planning owners need deliberate reconciliation after approval. Current main must not be described as already containing either PR.

## Inspection method and evidence

`evidence/*-source-index.jsonl.gz` contains path, byte length, SHA-256 and static import/export/function anchors. Python files parsed under the host's Python 3.12 with zero reported parse errors; parsing is not runtime compatibility. TS/JS uses regex indexing, not a compiler-verified module graph. Test-named paths are filename counts, not executed test cases. The source manifest, plugin manifests, tool registration sites, skill packages, English Hermes docs and OpenClaw docs are cross-indexed in the master matrix. Dynamic/table-driven registrations remain identified as expressions where their names cannot safely be resolved statically. Nothing from either reference runtime was imported to discover its capabilities.

{table(['Surface','OpenClaw','Hermes','Interpretation'],[
('Plugin manifest files',META['openclaw']['plugin_manifests'],META['hermes']['plugin_manifests'],'Declarations; not all are channels or independent capabilities'),
('SKILL.md files',META['openclaw']['skills'],META['hermes']['skills'],'Instruction/resource packages, including optional/fixture/vendor paths; not neural weights'),
('Indexed doc pages',META['openclaw']['documents'],META['hermes']['documents'],'Coverage anchors; overlap/overview pages are not unique features')])}

The matrix has {SUMMARY['rows']} labeled coverage records. It preserves overlaps between core behavior, manifests, concrete integration identities, tool declarations, skills, documentation and external catalog entries rather than inflating a unique-capability count. {SUMMARY['by_entry_type']['catalog_reference']} Hermes external catalog references are individually tracked and blocked on external source/license review; their implementation is outside the three repos and has not been audited here.

Evidence lives in `repositories.json`, `dependency-declarations.json`, `license-inventory.json`, `plugin-manifests.json`, `tool-registrations.json`, `documentation-index.json`, `skill-packages.json` and the compressed source indexes. These are source declarations, not a resolved installed SBOM or evidence of service access.

## Traced architecture boundaries

OpenClaw: CLI → gateway ownership/database admission → HTTP/WebSocket handshake → scoped request dispatch → admitted run → agent tool loop → per-turn authority gate → plugin/sandbox effect → event/result persistence. Its protocol frames are its own versioned RPC, not MCP. Its memory engine is under `extensions/memory-core`, and its current cron store is SQLite-backed. See [OpenClaw detail](OPENCLAW_REVERSE_ENGINEERING.md).

Hermes: CLI/gateway/TUI → `AIAgent` facade → durable turn admission → context/request construction → response normalization → tool rounds → sequential/parallel executor → registry/approval/backend → finalization/persistence. Memory providers, skill operations and curator hooks are separate owners; learning artifacts are not new foundation weights. See [Hermes detail](HERMES_REVERSE_ENGINEERING.md).

Zenith: current Agent/context/provider lock and SQLite owners remain authoritative. PR19 adds a supervised queue, fixed diagnostic approvals/events and metadata HMAC history; it does not generate autonomous model tool calls, execute general code, run subagents or host channels. See [current Zenith architecture](ZENITH_CURRENT_ARCHITECTURE.md).

## Runtime and trust compatibility findings

S: Hermes top-level `requires-python` is >=3.11,<3.15, but `.python-version`, PM's project/lock and Python-version markers target the managed 3.14 runtime. Its desktop/root Node engines require >=26. Many app dependencies are only declared for >=3.14; a bare import/install into Zenith 3.12 is not a supported reuse strategy. Sources: {h('pyproject.toml','requires-python')}, {h('pm/pyproject.toml')}, {h('.python-version')}, {h('package.json')}, {h('apps/desktop/package.json')}.

S: Hermes `model_tools.py` discovers tools and plugins at import; its plugin loader can execute Python in the agent process. Default terminal configuration is local host execution. These are deliberate personal-agent trust assumptions, not proof of an exploit. Zenith's multi-account server and requested untrusted-execution boundary require a stricter broker/worker design. Sources: {h('model_tools.py','discover_builtin_tools()')}, {h('hermes_cli/plugins.py')}, {h('hermes_cli/config_defaults.py','"backend": "local"')}, {h('SECURITY.md')}.

S: OpenClaw's sandbox resolver defaults to off, and some compatibility HTTP shared-secret endpoints intentionally use full operator scope. Do not adopt those defaults as Zenith's account/admin model. Sources: {o('src/agents/sandbox/config.ts','mode:')}, {o('src/gateway/http-endpoint-helpers.ts')}.

## Executable baseline and limits

M: Fresh cloned-main suite ran **243 tests, 242 passed, one skipped, 33.364 s**. The existing trained HF/LoRA checkpoint loaded offline; arithmetic/geography probes returned `4` and `Paris` on direct and routed paths. Adapter/profile hash checks passed. These two probes do not establish broad intelligence, agent competence, security parity or faster performance.

Earlier PR19 evidence is reused at its unchanged commit: 277 local tests (one skip), seven remote Windows/Linux/container checks plus the diagnostic watch passed. Its three-pair CPU queued-chat median was slower than legacy chat (9855.643 vs 6423.591 ms); no speedup is claimed. Reference runtimes, external channels, native companion apps, Docker/VM execution and GPU benchmarks were not run in this audit. Host Python 3.12/Node 24.19.0 do not satisfy the references' full supported runtime requirements; no service credentials are configured in the managed environment.

No new unified parity is VERIFIED. Baseline measurements, source declarations and proposed acceptance tests are separated throughout this package.
''')
put('HERMES_REVERSE_ENGINEERING.md',f'''# Hermes Agent: source-level analysis

{COMMON}

## Scope, installation and declared platforms

The pinned Hermes tree has {META['hermes']['tracked_files']} tracked files and {META['hermes']['python_modules']} Python modules, including a large test tree. Its package metadata reports version 0.0.0, so commit identity is more precise than inferring a published release version. Root dependencies declare Python >=3.11,<3.15 for updater compatibility while the managed runtime/lock uses 3.14; core dependency markers mostly require >=3.14. Desktop and root JS packages require Node >=26; the root npm engine excludes >=11.10.0,<11.17.0. Source: {h('pyproject.toml')}, {h('pm/pyproject.toml')}, {h('pm/uv.lock')}, {h('package.json')}, {h('apps/desktop/package.json')}.

D: Platform documentation prioritizes macOS Apple Silicon desktop, Windows CLI/MSIX, Linux/WSL2 CLI and Docker; Nix and Android/Termux aarch64 are best effort. Windows MSIX requires Windows 11 22H2+, some architectures/dependencies have limits, Intel macOS/Termux release builds are optional, and Linux desktop packaging is disabled in its release workflow despite local build paths. PyPI/brew/AUR installation is explicitly not a supported distribution method. These are upstream support policies, not host tests completed here: {h('website/docs/getting-started/platform-support.md')}.

P: Zenith retains its ordinary Python/venv installation and existing 3.10/3.12 support. Selected pure logic can be adapted with notices and compatibility tests; an isolated version-pinned worker may use another runtime when necessary. Do not install a second Hermes agent daemon or replace Zenith with `AIAgent`.

## Entry points, turn lifecycle and call graph

S: `run_agent.py` exposes `AIAgent` through multiple narrowly owned mixins. `TurnFacadeMixin.run_conversation` coordinates foreground/background admission, durable session leases, accounting/profile scopes and cleanup around `agent.conversation_loop.run_conversation`. Context/request/response/tool/finalization phases live in sibling modules. Sources: {h('run_agent.py','class AIAgent')}, {h('agent/turn_facade.py','def run_conversation')}, {h('agent/turn_facade_lease.py')}, {h('agent/conversation_loop.py')}, {h('agent/turn_context.py')}, {h('agent/turn_request_assembly.py')}, {h('agent/turn_response_intake.py')}, {h('agent/turn_tool_round.py')}, {h('agent/turn_finalizer.py')}.

```mermaid
flowchart TD
  Entry[CLI / gateway / TUI / desktop] --> Facade[AIAgent facade]
  Facade --> Lease[Durable turn admission / profile scope]
  Lease --> Context[Context snapshot / memory / compression]
  Context --> API[Provider request and streamed response]
  API --> Decision[Response normalization and budget checks]
  Decision --> Tools[Tool round / segmented executor]
  Tools --> Registry[Tool registry and write approvals]
  Registry --> Backend[Local / container / remote / plugin backend]
  Backend --> Context
  Decision --> Final[Finalization / transcript / usage]
  Final --> Learning[Memory sync / review / skill usage]
```

The loop handles interruption/redirection, tool argument normalization, empty replies, provider failures, truncation and context pressure. These are source-level implemented paths; exact reliability/latency has not been measured here. Selected sources: {h('agent/turn_empty_response.py')}, {h('agent/turn_loop_errors.py')}, {h('agent/turn_liveness.py')}, {h('agent/interrupt_control.py')}.

## Tool registry, discovery and parallel execution

S: Tools self-register schemas/handlers/check functions through `tools.registry`. `model_tools.py` imports built-in tool modules and discovers plugins, then serves tool definitions and dispatch. Toolsets separate core, coding, GUI and webhook-safe surfaces; service reachability checks do not themselves establish authorization. Table-driven definitions and per-session overlays mean a static schema count is not the runtime tool set for an account. Sources: {h('tools/registry.py','def discover_builtin_tools')}, {h('model_tools.py')}, {h('toolsets.py','_HERMES_CORE_TOOLS')}, {h('agent/tool_executor.py')}, {h('agent/terminal_approval_batch.py')}.

Native tools cover terminal/process control, file operations, web retrieval, browser/CDP/dialog/vault, vision/media, memory/session search, todos, skills, delegation, schedules, kanban and client-specific controls. The matrix tracks individual declarations/toolset members and service gates. Do not equate webhook-safe or default toolset names with capability grants in Zenith.

S: Terminal backends include local, Docker, SSH, Modal, managed Modal, Daytona and Vercel paths. Default configuration uses local host execution; some cloud backends require accounts/tokens and specific lifecycle controls. Docker egress and local subprocess-environment policies are separate. File tools use the backend shell contract. Sources: {h('hermes_cli/config_defaults.py','"backend": "local"')}, {h('tools/terminal_tool_backends.py')}, {h('tools/environments/local.py')}, {h('tools/environments/local_env_policy.py')}, {h('tools/environments/docker.py')}, {h('tools/environments/docker_egress.py')}, {h('tools/environments/ssh.py')}, {h('tools/file_operations.py')}.

S/D: Hermes's security policy is explicitly single-tenant and treats OS isolation as the boundary against an adversarial model. A container terminal does not isolate in-process plugin/hooks, MCP subprocesses or every execution path. This is an architectural trust assumption, not a vulnerability finding or an escape test. Zenith must put untrusted executable effects behind its own least-privilege broker and isolated workers: {h('SECURITY.md','## 2. Trust Model')}, {h('tools/code_execution_tool.py')}.

## State and memory are separate learning layers

S: `hermes_state.py` is a SQLite/WAL facade over schema/session/message/search/compression/maintenance owners. It stores source-tagged sessions and lineage; batch/RL trajectories are separate. Built-in curated memory is bounded file-backed MEMORY.md / USER.md, with locking, validation and backup/drift safeguards. It is not a built-in universal vector database or a neural weight update. Sources: {h('hermes_state.py')}, {h('hermes_state_schema.py')}, {h('hermes_state_search.py')}, {h('tools/memory_tool_store.py')}.

S: `MemoryManager` fans lifecycle/prefetch/sync/tool hooks to the built-in provider plus at most one external plugin provider. It binds caller/profile context across workers, scrubs egress and bounds stuck/inflight calls. Provider checkpoint API v2 supports strict pre-compression handoffs. Sources: {h('agent/memory_manager.py')}, {h('agent/memory_provider.py','PRE_COMPRESS_CHECKPOINT_API_VERSION')}, {h('agent/memory_caller_scope.py')}, {h('agent/conversation_compression_checkpoint.py')}.

D/S: The two in-tree external memory plugins are RetainDB and ByteRover; additional advertised systems such as Honcho, Mem0, OpenViking, Hindsight, Holographic and Supermemory are catalog integrations outside this tree. They may require external repositories, SDKs, cloud/self-hosted services and permission to export conversation data. Source: {h('website/docs/user-guide/features/memory-providers.md')}, {h('plugins/memory/retaindb/plugin.yaml')}, {h('plugins/memory/byterover/plugin.yaml')}. The catalog references are tracked separately as blocked, not claimed source-inspected implementations.

S: Context compression has checkpoint, archive, summary, tail, retry and timeout owners. Prompt/system/tool surfaces are restored/pinned per conversation where supported; skills/config updates may be deferred rather than mutating cached prefixes. Source: {h('agent/context_compressor.py')}, {h('agent/conversation_compression.py')}, {h('agent/prompt_cache_scope.py')}, {h('agent/conversation_loop.py','_restore_or_build_system_prompt')}.

P: Reuse Zenith's current SQLite, notes, summaries and ownership. Add scoped derived semantic/episodic/search records, preserve old shared-corpus semantics, and explicitly version context snapshots. Model context compression must not silently delete user history, lose tool-call/result pairs, cross accounts or present summaries as verified truth.

## Skill learning, versioning and curator

S: `skill_manage` supports create/edit/patch/delete/supporting-file operations, bounded content/frontmatter, mutation locks, provenance, usage and ledgered changes. Hub paths, optional/bundled sync, scanning and AST inspection are distinct owners. Sources: {h('tools/skill_manager_tool.py','def skill_manage')}, {h('tools/skill_manager_guards.py')}, {h('tools/skill_usage.py')}, {h('tools/skill_ledger.py')}, {h('tools/skill_provenance.py')}, {h('tools/skills_hub_install.py')}, {h('tools/skills_guard.py')}.

S: Skill write approval can stage writes, bind origin and replay approved payloads. The skill-manager helper explicitly fails open when its write-approval import is unavailable; agent-created skill security scanning is opt-in by default. These source choices must not be mistaken for mandatory isolation/review of all generated code. No exploit has been attempted. Sources: {h('tools/skill_manager_tool.py','def _run_write_gate')}, {h('tools/skill_manager_tool.py','def _guard_agent_created_enabled')}, {h('tools/write_approval.py')}.

S: Curator is enabled by default for deterministic lifecycle transitions; model-based consolidation is separately **off by default**. Reviews can snapshot skills and run a skills-only AIAgent fork with mutation provenance/guards and reports. Its ledger/backup safeguards are useful, but are not held-out task evaluation or evidence that the foundation model acquired new weights. Sources: {h('agent/curator.py','def is_enabled')}, {h('agent/curator.py','def run_curator_review')}, {h('agent/curator_backup.py')}.

P: Zenith uses candidate → isolated behavioral tests → reviewed activation → version/rollback. All skill/code mutation stays inactive until review. Training trajectories carry consent/license/provenance and exclude secrets, held-out fixtures and provider output without permitted training rights. Optional neural continuation calls Zenith's existing CPT/SFT/DPO/checkpoint/deployment owners, never random initialization or automatic promotion.

## Multi-agent and durable automation

S: Delegation supports leaf/orchestrator roles, fresh child contexts, task/workspace identity, bounded concurrency/depth/time, filtered toolsets and control/progress/results. Source: {h('tools/delegate_tool.py')}, {h('tools/delegate_tool_config.py')}, {h('tools/delegate_tool_child_run.py')}, {h('tools/delegate_tool_toolsets.py')}, {h('tools/async_delegation.py')}, {h('tools/delegate_tool_registry.py')}.

S: Kanban provides task coordination/review/heartbeat/block/attachments and dispatcher state, while mixture-of-agents coordinates model responses separately. Neither is evidence of weight merging. Sources: {h('tools/kanban_tools.py')}, {h('hermes_cli/kanban.py')}, {h('agent/moa_loop.py')}, {h('agent/moa_trace.py')}.

S: Hermes cron stores jobs in **JSON** under the profile cron directory with locks, claims, schedule/timezone handling and output/delivery paths. This differs from the audited OpenClaw SQLite scheduler. Sources: {h('cron/jobs.py')}, {h('cron/scheduler.py')}. P: a unified Zenith scheduler should reuse its SQLite transactional owner, not install a second jobs.json scheduler and state database.

## Gateway, channels, MCP, interfaces and media

S: GatewayRunner handles configured adapters, session/runtime caches, platform lifecycle, dispatch and profile binding. Platform registration separates passive dependency probes from active dependency preparation; status displays are not supposed to install services. PlatformEntry carries sender/account policies, target resolution, streaming/media and delivery metadata. Sources: {h('gateway/run.py')}, {h('gateway/platform_registry.py','class PlatformEntry')}, {h('gateway/run_adapters.py')}.

The matrix separately records all 27 platform manifests, concrete registration variants (including WeCom callback and relay), source-backed tool/GUI/provider plugins and catalog entries. A platform manifest's existence is not proof of an owned account or device test. Telegram, Slack, Discord, WhatsApp modes, Matrix, Teams, Feishu, WeCom/Weixin and other adapters must each retain their own authentication, media/thread and delivery acceptance profile.

S: MCP owners cover stdio, SSE and streamable HTTP, OAuth/device flows, connection identity, schema caching, scope/trust metadata, bounded transport and dispatch. MCP descriptions/results remain external data. Source: {h('tools/mcp_tool_transport.py')}, {h('tools/mcp_tool_registration.py')}, {h('tools/mcp_oauth.py')}, {h('tools/mcp_schema_cache.py')}.

S: The CLI, Ink TUI + Python JSON-RPC backend, web SPA and Electron desktop are distinct surfaces on the agent engine. Browser/CDP and vault are distinct from computer input/capture; voice/STT/TTS/video/image handling require compatible backends. Sources: {h('cli.py')}, {h('ui-tui/package.json')}, {h('tui_gateway/server.py')}, {h('web/package.json')}, {h('apps/desktop/package.json')}, {h('tools/browser_use_cli.py')}, {h('tools/browser_vault_tool.py')}, {h('tools/computer_use/tool.py')}, {h('tools/voice_mode.py')}, {h('tools/vision_tools.py')}.

## What the audit does not establish

No Hermes dependency manager, plugin, tool, application, test runner or external service was executed. No comparison validates the README's exclusivity claim about being the only self-improving agent, nor its broad cost/latency marketing statements. No proprietary model's weights or hidden reasoning are accessed. The project is useful source for agent infrastructure; importing/rebranding it does not meet the mission's requirement that Zenith remain the model and primary unified engine.
''')
(E/'report-source-citations.json').write_text(json.dumps(CITATIONS,indent=2)+'\n')
