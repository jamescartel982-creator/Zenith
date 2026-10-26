from pathlib import Path
import ast,collections,csv,hashlib,json,re
import yaml
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';R=ROOT/'reports'
REPOS={'openclaw':Path('/workspace/openclaw-review-20261025/openclaw'),'hermes':ROOT/'hermes-agent','zenith-main':ROOT/'zenith-main','zenith-pr19':Path('/workspace/zenith-platform')}
META=json.loads((E/'repositories.json').read_text())
URL={'openclaw':'openclaw/openclaw','hermes':'NousResearch/hermes-agent','zenith-main':'jamescartel982-creator/Zenith','zenith-pr19':'jamescartel982-creator/Zenith'}
CITATIONS=[]
def source(repo,path,pattern=None):
 p=REPOS[repo]/path;assert p.is_file(),(repo,path)
 data=p.read_text(encoding='utf8',errors='replace');line=1
 if pattern:
  assert pattern in data,(path,pattern)
  line=data.count('\n',0,data.index(pattern))+1
 sha=META[repo]['commit'];url=f'https://github.com/{URL[repo]}/blob/{sha}/{path}#L{line}'
 out={'repository':repo,'commit':sha,'path':path,'line':line,'url':url}
 CITATIONS.append(out);return out
GROUPS={
'G00':{'title':'Baseline, approval and existing-PR reconciliation','deps':[],'dest':['scripts/platform_protection.py','docs/unified-platform/compatibility.md'],'tests':['tests/test_platform_protection.py'],'accept':'Verify pinned baseline/model/tokenizer hashes, PR19 divergence and rollback backup; no original checkpoint mutation.','security':'No source edits or activation before approval; do not overwrite original data.'},
'G01':{'title':'Identity, policy, schemas, audit and secrets','deps':['G00'],'dest':['agent/permissions.py','agent/approvals.py','agent/audit_chain.py','agent/platform_migrations.py','agent/secret_broker.py'],'tests':['tests/test_unified_permissions.py','tests/test_unified_migrations.py'],'accept':'Deny forged actors, stale MFA/grants, cross-account references and post-approval argument changes with zero side effects; preserve old DB writers.','security':'Server-owned identity; capability/action grants and emergency stop, secret references only.'},
'G02':{'title':'Isolated execution, files, shell, Git and egress','deps':['G01'],'dest':['agent/sandbox.py','agent/sandbox_docker.py','agent/filesystem_tools.py','agent/shell_tools.py','agent/git_tools.py','agent/egress_policy.py'],'tests':['tests/test_unified_sandbox.py','tests/e2e/test_unified_execution.py'],'accept':'Owned container/VM runs real bounded tools; reject forbidden file/network/process access, junction/symlink escapes and missing sandbox; no host fallback.','security':'No unrestricted model shell; rootless/nonroot workers, quotas, pinned images, approvals and network deny by default.'},
'G03':{'title':'Typed model turns and autonomous runtime','deps':['G01','G02'],'dest':['agent/model_capabilities.py','agent/providers.py','agent/tool_protocol.py','agent/tool_registry.py','agent/autonomy.py','agent/planning.py','agent/verification.py','agent/runtime.py'],'tests':['tests/test_unified_model_turns.py','tests/integration/test_unified_autonomy.py'],'accept':'Actual selected Zenith checkpoint completes frozen multi-step workflows with valid schemas, error recovery, budgets, attribution and cancellation; malformed calls have no effects.','security':'Model output is a proposal, never authorization; preserve generate/stream and current model weights.'},
'G04':{'title':'Durable sessions, tasks, events, HTTP/WebSocket/CLI','deps':['G03'],'dest':['agent/task_store.py','agent/event_bus.py','agent/session_manager.py','agent/gateway.py','agent/server.py','agent/websocket_gateway.py','agent/task_cli.py','agent/commands.py'],'tests':['tests/integration/test_unified_gateway.py','tests/e2e/test_unified_recovery.py'],'accept':'Real HTTP/WS admission, replay, ownership, lease fencing and restart/cancel; uncertain non-idempotent writes reconcile instead of replay.','security':'Authenticate and scope live/replayed events; bounded frames/queues; no global bearer-to-owner promotion.'},
'G05':{'title':'Persistent scoped memory and context compression','deps':['G01','G04'],'dest':['agent/retrieval.py','agent/semantic_memory.py','agent/episodic_memory.py','agent/context_manager.py','agent/history_search.py'],'tests':['tests/test_unified_memory.py','tests/integration/test_unified_compression.py'],'accept':'Account/project recall, deletion/TTL, provenance, bounded context, compression checkpoint/recovery and retrieval relevance on frozen labels; no private/shared-corpus crossover.','security':'Treat retrieved text/inferences as data, isolate namespaces and redact provider egress; no duplicate personal-memory DB.'},
'G06':{'title':'Reviewed learning, trajectories, skill candidates and workflow discovery','deps':['G03','G05'],'dest':['agent/trajectory_store.py','agent/skill_learning.py','agent/skill_evaluation.py','agent/skill_versions.py','agent/workflow_discovery.py','agent/continual.py','agent/checkpoints.py','agent/deployment.py'],'tests':['tests/test_unified_skill_learning.py','tests/integration/test_unified_learning_cycle.py'],'accept':'Generate a real candidate from consented successful/failed traces, test on independent fixtures, review/activate/version/rollback; optional continued training preserves parent and retained quality.','security':'No unreviewed live code/weight changes; exclude secrets, held-out data and provider outputs without permitted training rights.'},
'G07':{'title':'Plugin/skill packages, MCP and dynamic discovery','deps':['G01','G02','G04'],'dest':['agent/plugins/manifest.py','agent/plugins/registry.py','agent/plugins/worker.py','agent/skill_packages.py','agent/mcp_client.py','agent/mcp_registry.py'],'tests':['tests/test_unified_plugin_integrity.py','tests/integration/test_unified_mcp.py'],'accept':'Pinned manifest/schema/protocol negotiation, actual isolated invocation, tool/resource discovery, cancellation, auth/revocation and upgrade reapproval; malformed packages fail closed.','security':'No untrusted import in host; discovery is not permission or implicit dependency installation.'},
'G08':{'title':'Supervisor, specialist children and shared task graph','deps':['G03','G04','G07'],'dest':['agent/multi_agent.py','agent/specialists.py','agent/task_graph.py','agent/workspace_manager.py'],'tests':['tests/integration/test_unified_multi_agent.py'],'accept':'Real supervisor/child goal completion, isolated workspaces, strict-subset grants, collective budgets, cancel/steer, blocked-input/review handoff and recovery.','security':'No automatic parent admin-cookie/MFA inheritance, no model self-elevation or unauthenticated inter-agent events.'},
'G09':{'title':'Channels, identity routing, notifications and delivery','deps':['G01','G04','G07'],'dest':['agent/channels/base.py','agent/channel_registry.py','agent/identity_router.py','agent/outbox.py'],'tests':['tests/integration/test_unified_channels.py','tests/e2e/test_unified_channel_accounts.py'],'accept':'Each separately inventoried service proves owned-account pairing, valid/invalid signatures, replay rejection, text/media/thread semantics and uncertain-send reconciliation; no test double counts as live service verification.','security':'Explicit account/chat/thread bindings, allowlists, message-send approvals, scoped credentials and PII-safe metadata.'},
'G10':{'title':'Schedules, heartbeat, triggers and event workflows','deps':['G04','G08','G09'],'dest':['agent/scheduler.py','agent/triggers.py','agent/heartbeat.py','agent/workflow_runner.py'],'tests':['tests/integration/test_unified_scheduler.py'],'accept':'Durable UTC/cron+timezone jobs with tested DST/misfire/overlap policy, standing-authority expiry, event dedup and restart recovery.','security':'Never reuse expired login/MFA sessions as permanent job authority; approve external effects individually or with narrow standing grants.'},
'G11':{'title':'Browser, computer, remote environments and credential vault','deps':['G02','G04','G07'],'dest':['agent/browser_automation.py','agent/computer_automation.py','agent/remote_execution.py','agent/browser_vault.py'],'tests':['tests/e2e/test_unified_browser.py','tests/e2e/test_unified_desktop.py','tests/e2e/test_unified_remote_hosts.py'],'accept':'Actual isolated browser/VM/owned SSH endpoint, all-subresource egress checks, private-profile exclusion, approval-bound writes, cancellation and cleanup; missing backend is unavailable.','security':'Do not import host cookies/keychains or send secrets to model context; origin-bind handles and human payment/credential actions.'},
'G12':{'title':'Multimodal documents, images, audio, video and voice','deps':['G03','G07','G09','G11'],'dest':['agent/multimodal/documents.py','agent/multimodal/vision.py','agent/multimodal/audio.py','agent/multimodal/speech.py','agent/multimodal/video.py'],'tests':['tests/e2e/test_unified_multimodal.py'],'accept':'Real licensed compatible backends with bounded files, OCR/STT/TTS/vision/media fixtures and declared failure/unsupported formats; preserve text-only installation.','security':'Do not splice an arbitrary encoder into Zenith embeddings; scan/limit media, isolate decoders and scope all provider egress.'},
'G13':{'title':'Provider and infrastructure connectors','deps':['G01','G03','G07'],'dest':['agent/model_registry.py','agent/provider_adapters/local_adapter.py','agent/connectors/base.py','agent/database_tools.py','agent/infrastructure_tools.py'],'tests':['tests/integration/test_unified_providers.py','tests/e2e/test_unified_infrastructure.py'],'accept':'Exact account-visible model IDs, local-default/privacy routing, errors/failover and actual least-privilege owned API/database/host operations; unsupported/restricted models unavailable.','security':'No account-access assumptions, no embedded keys, no secret-bearing provider output in training without permission.'},
'G14':{'title':'CLI/TUI/web/desktop/mobile applications','deps':['G04','G08','G09','G12'],'dest':['agent/web/platform.js','agent/web/index.html','agent/web/app.js','agent/web/style.css','clients/tui/package.json','clients/tui/src/main.ts','clients/desktop/package.json','clients/desktop/src/main.ts','clients/android/app/src/main/java/ai/zenith/CompanionActivity.kt','clients/ios/ZenithCompanion/App.swift'],'tests':['tests/e2e/test_unified_ui.py','clients/tui/tests/session.test.ts','clients/desktop/tests/gateway.test.ts'],'accept':'Real target-OS builds, login/task/approval/reconnect/accessibility/media workflows and identity/model attribution; no native-client claim from Linux-only unit tests.','security':'Keep Zenith branding/core; transport owns auth, renderer cannot grant permissions, platform prompts/signing/entitlements respected.'},
'G15':{'title':'Packaging, deployment, benchmarks and acceptance release','deps':['G04','G06','G08','G10','G11','G12','G13','G14'],'dest':['scripts/unified_benchmark.py','agent/evaluation/unified-platform-v1.json','agent/telemetry.py','agent/monitoring.py','pyproject.toml','install.py','Dockerfile','compose.yaml','.github/workflows/unified-platform.yml','THIRD_PARTY_NOTICES.md'],'tests':['tests/test_unified_installation.py','tests/e2e/test_unified_acceptance.py'],'accept':'Frozen paired reference/Zenith tests, security/retention/performance regressions, Windows/Linux CPU and optional GPU/remote/container/companion jobs, model-hash and rollback drills; publish only actual results.','security':'Default-off experiments, immutable parent checkpoint, signed/pinned artifacts and dependency notices; no automatic unverified deployment.'},
}
ROWS=[]
def add(project,kind,name,paths,group,status='NOT STARTED',main='None',pilot='None',missing=None,extra=None):
 refs=[source(project,p) for p in paths]
 g=GROUPS[group]
 equivalents={
 'G01':('agent/admin.py, owner_mfa.py, execution.py: existing owner/MFA/fixed grants','agent/permissions.py, approvals.py, audit_chain.py: scoped supervised pilot'),
 'G03':('agent/core.py/providers.py: text inference; orchestration.py: optional model federation','Explicit submitted diagnostics; no autonomous model tool turns'),
 'G04':('agent/server.py: authenticated HTTP/SSE chat and private account/conversation APIs','agent/gateway.py/task_store.py/event_bus.py: supervised queue/leases/events'),
 'G05':('agent/personal.py/summaries.py and storage.py: notes, manual summary and shared lexical corpus','Existing memory preserved; project retrieval unavailable'),
 'G06':('agent/continual.py/checkpoints.py/deployment.py: reviewed neural continuation and rollback; no skill learner','No automatic skill-learning/trajectory engine'),
 'G07':('agent/skills.py/skill_access.py: bounded prompt profiles; model adapters are trusted transports','No executable plugins or MCP client'),
 'G08':('agent/model_federation.py: multiple model responses, not multiple executing agents','No subagent/workspace executor'),
 'G09':('No messaging service adapters; existing account identity only','No external messaging/outbox integration'),
 'G10':('No user automation scheduler; CI diagnostic watch is separate','No user scheduler'),
 'G11':('No browser/computer/remote executor; browser.py opens the chat UI','Unavailable'),
 'G12':('Text execution; multimodal model references are metadata only','No media executor'),
 'G13':('agent/model_registry.py/provider_adapters: account-scoped text providers; no infrastructure executor','Existing provider interfaces preserved'),
 'G14':('agent/cli.py and agent/web/: existing terminal CLI and plain-JS UI','UI unchanged; no task panels/native companions'),
 'G15':('install.py, launchers, Dockerfile and current CI','Default installation unchanged; pilot CI tests added'),
 'G02':('agent/execution.py: seven fixed bounded diagnostics; no general shell/file/code sandbox','Same fixed diagnostics; no general sandbox'),
 }
 if main=='None':main=equivalents.get(group,('None','None'))[0]
 if pilot=='None':pilot=equivalents.get(group,('None','None'))[1]
 row={'id':f'F{len(ROWS)+1:05d}','reference_project':project,'entry_type':kind,'feature_name':name,'source_evidence':'S' if kind not in {'documentation_surface','skill_package','catalog_reference'} else 'D',
      'sources':refs,'configuration_and_dependencies':f'Pinned {project} declarations in evidence/dependency-declarations.json; feature owner/config paths linked above. Runtime availability is not proven by metadata.',
      'zenith_main_equivalent':main,'zenith_pr19_equivalent':pilot,'missing_implementation':missing or g['title'],
      'integration_strategy':g['title']+' through shared Zenith owners; not a second agent runtime',
      'destination_files':g['dest'],'security_implications':g['security'],'acceptance_test_files':g['tests'],
      'acceptance_behavior':g['accept'],'status':status,'group':group,'reference_runtime_tested':False,
      'verification_note':'No unified/reference-equivalent executable acceptance has passed in this audit. Existing Zenith baseline evidence is separate.'}
 if extra:row.update(extra)
 if extra and 'manifest_path' in extra:
  config_parts=['Manifest '+extra['manifest_path']]
  names=[v.get('name') if isinstance(v,dict) else str(v) for v in extra.get('required_environment_names',[])]
  if names:config_parts.append('required environment variable NAMES (not values): '+', '.join(str(x) for x in names))
  if extra.get('declared_description'):config_parts.append('declared feature profile: '+str(extra['declared_description']).strip())
  config_parts.append('Exact dependency and schema declarations: evidence/dependency-declarations.json and plugin-manifests.json; resolve/lock/review before implementation')
  row['configuration_and_dependencies']='; '.join(config_parts)
 ROWS.append(row);return row
# Curated behavioral contracts: exact implementation owners rather than README inference.
CORE=[
('hermes','Autonomous model/tool/result turn loop',['run_agent.py','agent/turn_facade.py','agent/conversation_loop.py','agent/turn_tool_round.py'],'G03','PARTIAL','Agent text generation only','Explicit supervised plans; no model-generated calls'),
('openclaw','Streamed tool loop and parallel batches',['packages/agent-core/src/agent-loop.ts','packages/agent-core/src/agent-loop-tool-execution.ts'],'G03','PARTIAL','Native token streaming','Fixed serial diagnostics; not autonomous batches'),
('hermes','Structured plans, todos and response verification',['tools/todo_tool.py','agent/conversation_loop.py','agent/turn_finalizer.py'],'G03','NOT STARTED','No native autonomous plan loop','No model-generated plan loop'),
('hermes','Segmented sequential/parallel tool execution',['agent/tool_executor.py','agent/terminal_approval_batch.py'],'G03','PARTIAL','Seven fixed synchronous diagnostics','Explicit plans and cancellation only'),
('hermes','Durable session turn admission and liveness',['agent/turn_facade.py','agent/turn_facade_lease.py','agent/turn_liveness.py'],'G04','PARTIAL','Account/conversation persistence','Task leases/reconciliation; no autonomous session ownership'),
('hermes','Tool error and empty-output recovery',['agent/turn_loop_errors.py','agent/turn_empty_response.py'],'G03','PARTIAL','Existing provider errors/deadlines','No autonomous repair cycle'),
('hermes','Interrupt, redirect and long-running background work',['agent/interrupt_control.py','tools/async_delegation.py','tools/terminal_tool_background.py'],'G04','PARTIAL','Token-stream cancellation','Supervised task cancel; no process/delegation runtime'),
('hermes','Provider routing, fallbacks and credential pools',['hermes_cli/fallback_config.py','agent/delegation_provider.py','run_agent.py'],'G13','PARTIAL','Registry/orchestration account-scoped text routing','Preserved existing routing; queued hybrid unavailable'),
('openclaw','Versioned WebSocket connect and gateway RPC',['packages/gateway-protocol/src/schema/frames.ts','src/gateway/server/ws-connection/message-handler.ts'],'G04','NOT STARTED','HTTP/SSE only','HTTP/SSE pilot; no OpenClaw protocol'),
('openclaw','Gateway lifecycle, ownership and deferred startup',['src/gateway/server.ts','src/gateway/server-start.ts'],'G04','PARTIAL','FastAPI application lifecycle','Optional worker lifespan and additive storage'),
('hermes','Multi-platform gateway lifecycle and session routing',['gateway/run.py','gateway/run_adapters.py','gateway/session.py'],'G09','PARTIAL','Accounts/conversation access only','No external messaging'),
('hermes','HTTP/OpenAI-compatible agent API and room authority',['gateway/platforms/api_server.py','gateway/platforms/api_server_openai_routes.py','gateway/platforms/api_server_room_grants.py'],'G04','PARTIAL','Zenith-specific chat HTTP/SSE','Supervised task HTTP; no provider API parity'),
('hermes','TUI/desktop JSON-RPC backend',['tui_gateway/server.py','ui-tui/package.json'],'G14','NOT STARTED','Simple terminal CLI and web UI','No TUI/desktop RPC'),
('hermes','Bounded curated cross-session MEMORY.md / USER.md',['tools/memory_tool.py','tools/memory_tool_store.py'],'G05','PARTIAL','Account-owned explicit SQLite notes','Preserved notes; no automatic memory extraction'),
('hermes','Pluggable memory lifecycle and scoped egress',['agent/memory_manager.py','agent/memory_provider.py','agent/memory_caller_scope.py'],'G05','NOT STARTED','No external memory provider engine','Project retrieval explicitly unavailable'),
('hermes','Conversation search with lineage-aware results',['tools/session_search_tool.py','hermes_state.py'],'G05','PARTIAL','Conversation listing/history','No cross-session search API'),
('openclaw','Scoped hybrid semantic/lexical retrieval',['extensions/memory-core/src/memory/manager.ts','extensions/memory-core/src/memory/hybrid.ts'],'G05','PARTIAL','Shared lexical corpus and separate user notes','No scoped embeddings backend'),
('hermes','Context compression and durable pre-compression checkpoint',['agent/context_compressor.py','agent/conversation_compression.py','agent/conversation_compression_checkpoint.py'],'G05','PARTIAL','Manual account conversation summary','No automatic context checkpoint/compaction engine'),
('hermes','Per-conversation stable prompt/tool surfaces',['agent/prompt_cache_scope.py','agent/skills_index_delta.py','agent/turn_context.py'],'G05','PARTIAL','Context rebuilt per turn; no measured prefix reuse','Live authorization independent of context'),
('hermes','Skills list/view/create/edit/patch/delete',['tools/skills_tool.py','tools/skill_manager_tool.py','tools/skill_manager_guards.py'],'G06','PARTIAL','Built-in validated prompt/resource profiles','Same profiles; no generated package activation'),
('hermes','Skill usage feedback, ledger and provenance',['tools/skill_usage.py','tools/skill_ledger.py','tools/skill_provenance.py'],'G06','PARTIAL','Human-reviewed turn corrections and skill activation records','No candidate skill learning engine'),
('hermes','Curator review, consolidation, aging and backups',['agent/curator.py','agent/curator_backup.py'],'G06','NOT STARTED','No autonomous skill curation','No autonomous skill curation'),
('hermes','Third-party skill install and security inspection',['tools/skills_hub.py','tools/skills_hub_install.py','tools/skills_guard.py','tools/skills_ast_audit.py'],'G07','NOT STARTED','No executable skill package installation','Unavailable'),
('hermes','External skill source hubs and synchronization',['tools/skills_hub_sources.py','tools/skills_hub_clawhub.py','tools/skills_hub_github.py','tools/skills_sync.py'],'G07','NOT STARTED','Reference catalog only','No hub installer'),
('hermes','Trajectory and replay data for improvement',['hermes_state.py','agent/session_persistence.py','batch_runner.py'],'G06','PARTIAL','Approved native turn export and versioned curriculum','No execution trajectory learning'),
('openclaw','Plugin manifest discovery and runtime loading',['src/plugins/manifest.ts','src/plugins/discovery.ts','src/plugins/loader-module-runtime.ts'],'G07','NOT STARTED','Trusted model transport protocol only','Executable plugins unavailable'),
('hermes','Plugin discovery, scoped registration and package validation',['hermes_cli/plugins.py','hermes_cli/plugin_validate_private_imports.py','tools/registry.py'],'G07','NOT STARTED','No untrusted plugin host','Unavailable'),
('hermes','MCP stdio/SSE/streamable HTTP, OAuth and schema discovery',['tools/mcp_tool_transport.py','tools/mcp_oauth.py','tools/mcp_tool_registration.py','tools/mcp_schema_cache.py'],'G07','NOT STARTED','No MCP client','Unavailable'),
('hermes','Subagent leaf/orchestrator roles and strict tool surfaces',['tools/delegate_tool.py','tools/delegate_tool_child_run.py','tools/delegate_tool_toolsets.py'],'G08','NOT STARTED','Model federation is not subagent execution','No subagent executor'),
('hermes','Async delegation, steer/cancel and recovery',['tools/async_delegation.py','tools/delegate_tool_registry.py','tools/delegate_tool_dispatch.py'],'G08','NOT STARTED','No child task graph','Unavailable'),
('openclaw','Subagent spawn and durable registry',['src/agents/subagents/spawn/subagent-spawn.ts','src/agents/subagents/registry/subagent-registry.ts'],'G08','NOT STARTED','No subagent runtime','Unavailable'),
('hermes','Kanban task coordination, review lanes and attachments',['hermes_cli/kanban.py','tools/kanban_tools.py'],'G08','NOT STARTED','Human-review queue for chat only','No specialist task graph'),
('hermes','Skill/worktree-isolated coding agents and editor ACP',['acp_adapter/server.py','agent/delegation_backends.py','tools/delegate_tool_config.py'],'G08','PARTIAL','Coding provider routing only','No coding workspace/test runner'),
('hermes','Shell/process management with selectable environments',['tools/terminal_tool.py','tools/terminal_tool_backends.py','tools/process_registry.py'],'G02','NOT STARTED','No general shell','No general shell; sandbox unavailable'),
('hermes','Read/write/patch/search files and document extraction',['tools/file_tools.py','tools/file_operations.py'],'G02','NOT STARTED','Pasted-code offline audit only','No filesystem executor'),
('hermes','Programmatic tool execution via Python',['tools/code_execution_tool.py'],'G02','NOT STARTED','No general Python execution on main','No general code sandbox'),
('hermes','Docker execution backend',['tools/environments/docker.py','tools/environments/docker_egress.py'],'G02','NOT STARTED','Application Docker packaging only','No code sandbox'),
('hermes','SSH remote execution and file synchronization',['tools/environments/ssh.py','tools/environments/file_sync.py'],'G11','NOT STARTED','No remote execution','Unavailable'),
('hermes','Modal, Daytona and Vercel execution',['tools/environments/modal.py','tools/environments/daytona.py','tools/environments/vercel_sandbox.py'],'G11','NOT STARTED','No remote execution services','Unavailable'),
('hermes','CDP browser automation, dialogs and session lifecycle',['tools/browser_use_cli.py','tools/browser_cdp_tool.py','tools/browser_dialog_tool.py','tools/browser_session.py'],'G11','NOT STARTED','browser.py only opens chat page','Browser automation unavailable'),
('hermes','Browser vault origin-bound credential handles',['tools/browser_vault_tool.py','tools/browser_vault_context.py'],'G11','NOT STARTED','No credential-fill tool','Unavailable'),
('hermes','Computer input/capture with permission mediation',['tools/computer_use/tool.py','tools/computer_use/permissions.py','tools/computer_use/cua_backend.py'],'G11','NOT STARTED','No computer control','Unavailable'),
('openclaw','Browser auth, SSRF policy and privileged profile import',['extensions/browser/src/browser-tool.ts','extensions/browser/src/browser/ssrf-policy-helpers.ts'],'G11','NOT STARTED','No browser control','Unavailable; host-profile import not adopted by default'),
('openclaw','Computer interaction transport',['src/agents/tools/computer-tool.ts'],'G11','NOT STARTED','No computer tool','Unavailable'),
('hermes','Vision input normalization and history budgets',['tools/vision_tools.py','tools/vision_tools_image_prep.py','tools/vision_tools_history_budget.py'],'G12','PARTIAL','Catalog metadata is not a multimodal engine','Text-only executor'),
('hermes','Image and video generation providers',['tools/image_generation_tool.py','tools/image_generation_catalog.py'],'G12','NOT STARTED','No generation engine','Unavailable'),
('hermes','Audio containers, transcription and voice delivery',['tools/audio_container.py','tools/transcription_audio.py','gateway/platforms/base_streaming_tts.py'],'G12','NOT STARTED','No audio pipeline','Unavailable'),
('hermes','Browser preview and desktop display tools',['tools/read_terminal_tool.py','tools/annotate_preview_tool.py','tools/computer_use/tool.py'],'G14','NOT STARTED','No desktop preview','Unavailable'),
('hermes','Cron/interval scheduling and delivery',['cron/jobs.py','cron/scheduler.py','gateway/platforms/send_targets.py'],'G10','NOT STARTED','CI diagnostic cron is not per-user scheduling','Unavailable'),
('openclaw','Durable scheduler admission and authority',['src/cron/service.ts','src/cron/store.ts','src/cron/run-authority.ts'],'G10','NOT STARTED','No user scheduler','Unavailable'),
('openclaw','Channel ingress durable claims and events',['src/channels/message/ingress-drain.ts','src/infra/agent-events.ts'],'G09','NOT STARTED','No channel ingress','Task events only; no external delivery'),
('hermes','Webhook ingress, event routing and replay boundaries',['gateway/platforms/webhook.py','gateway/platforms/webhook_ingress.py','gateway/platforms/access_policy_mixin.py'],'G09','NOT STARTED','No external webhook surface','Unavailable'),
('hermes','Trust-scoped tool search and deferred schemas',['tools/tool_search.py','tools/registry.py','model_tools.py'],'G07','PARTIAL','Static fixed tool list; provider discovery separate','Fixed seven-tool registry, no semantic tool discovery'),
('hermes','Profile-aware configuration and context propagation',['hermes_constants.py','gateway/platform_registry.py','agent/memory_provider.py'],'G01','PARTIAL','Account/session isolation; env Settings','Server-derived ActorContext, not Hermes profiles'),
('openclaw','Operator scopes and current run authority',['src/gateway/operator-scopes.ts','src/agents/admitted-run-context.ts','src/agents/agent-tools.turn-authority.ts'],'G01','PARTIAL','Owner/MFA/fixed capability grants','Live session/revision and exact action approvals'),
('hermes','Child environment secret scrubbing',['tools/environments/local_env_policy.py','tools/environments/local.py','agent/redact.py'],'G01','PARTIAL','Owner-secret prompt guards','Redaction/canaries; no untrusted process environment yet'),
('openclaw','External-content boundaries and audit metadata',['src/security/external-content.ts','src/audit/audit-event-store.ts'],'G01','PARTIAL','Guarded prompts and local execution audit','Metadata HMAC history, not root-proof ledger'),
('hermes','CLI slash commands and interactive session controls',['cli.py','hermes_cli/main.py'],'G14','PARTIAL','Existing zenith terminal commands','Same CLI; no full TUI parity'),
('hermes','Web dashboard and file/terminal UI',['hermes_cli/web_server.py','web/package.json'],'G14','PARTIAL','Current plain-JS chat/admin/memory UI','No new task dashboard panels'),
('hermes','Electron desktop and SSH runtime management',['apps/desktop/package.json','hermes_cli/windows_ssh_runtime.py'],'G14','BLOCKED','No desktop companion','No desktop companion'),
('openclaw','Native macOS/iOS/Android companion applications',['apps/macos/Package.swift','apps/ios/project.yml','apps/android/build.gradle.kts'],'G14','BLOCKED','Web interface only','No native companions'),
('hermes','Packaging, updater and managed Python runtime',['pm/pyproject.toml','pm/environments.py','hermes_cli/update_cmd.py','hermes_cli/subcommands/update.py'],'G15','PARTIAL','Windows/Linux pip/venv local install','Install remains unchanged; no Hermes PM adoption'),
('hermes','Observability, tracing and accounting',['hermes_cli/observability/relay_shared_metrics.py','agent/aux_accounting.py'],'G15','PARTIAL','Bounded local generation metrics','Task metadata audit and existing metrics only'),
]
CORE.extend([
('hermes','Mixture-of-agents alternation, synthesis and trace',['agent/moa_loop.py','agent/moa_alternation.py','agent/moa_trace.py'],'G13','PARTIAL','Existing model federation/review/synthesis','Preserved federation; not specialist execution'),
('hermes','Voice conversation, interruption and wake engines',['tools/voice_mode.py','tools/voice_live.py','tools/wake_word.py','tools/wake_word_engines.py'],'G12','NOT STARTED','Text only','Unavailable'),
('hermes','Local/remote streaming TTS and speaker routing',['tools/tts_tool.py','tools/tts_streaming.py','tools/tts_tool_local.py'],'G12','NOT STARTED','No speech','Unavailable'),
('hermes','Video generation and media workflows',['tools/video_generation_tool.py','tools/xai_video_tools.py'],'G12','NOT STARTED','No media executor','Unavailable'),
('hermes','Source retrieval and bounded web extraction',['tools/web_tools.py','tools/web_tools_extract.py','tools/web_tools_rescue.py'],'G13','PARTIAL','Local source-linked lexical excerpts only','No live research executor'),
('hermes','Goals, personality and per-session context policy',['hermes_cli/goals.py','hermes_cli/personality.py','agent/conversation_loop.py'],'G14','PARTIAL','Prompt profiles, personal notes and summaries','Existing behavior preserved'),
('hermes','Hooks and event-driven outbound integration',['agent/shell_hooks.py','agent/outbound_webhooks.py','hermes_cli/hooks.py'],'G10','NOT STARTED','No untrusted hook executor','Unavailable'),
('hermes','Write-approval staging and skill mutation gates',['tools/write_approval.py','tools/skill_manager_tool.py'],'G01','PARTIAL','Owner/MFA capability grants','Exact diagnostic approvals; no skill mutation'),
('hermes','Language packs and localized interfaces',['agent/i18n_languages.py','hermes_cli/config_language.py'],'G14','NOT STARTED','Existing English UI','No localization package registry'),
])
for project,name,paths,group,status,main,pilot in CORE:
 add(project,'core_behavior',name,paths,group,status,main,pilot)
# Every manifest, channel/provider identity, skill, documentation page and external catalog entry is tracked.
manifests=json.loads((E/'plugin-manifests.json').read_text())
for item in manifests:
 project,path=item['repository'],item['path'];m=item.get('manifest') or {};name=str(m.get('id') or m.get('name') or Path(path).parent.name)
 channels=m.get('channels') or ([name] if m.get('kind')=='platform' else [])
 group='G09' if channels else 'G13' if m.get('kind')=='model-provider' or m.get('providers') or '/web/' in path else 'G05' if '/memory/' in path or m.get('kind')=='memory' else 'G07'
 if not channels and group=='G07':
  if any(t in name.lower() for t in ('browser','computer','facetime')):group='G11'
  elif any(t in name.lower() for t in ('voice','audio','speech','tts','video','image','media')):group='G12'
  elif any(t in name.lower() for t in ('cron','schedule','heartbeat')):group='G10'
  elif any(t in name.lower() for t in ('subagent','kanban')):group='G08'
 paths=[path];parent=REPOS[project]/Path(path).parent
 for candidate in ('index.ts','src/channel.ts','adapter.py','provider.py','__init__.py'):
  p=parent/candidate
  if p.is_file():paths.append(str(p.relative_to(REPOS[project])))
 extra={'manifest_id':name,'manifest_kind':m.get('kind'),'declared_description':m.get('description'),'config_schema_declared':bool(m.get('configSchema')),'required_environment_names':m.get('requires_env',[]),'manifest_path':path}
 add(project,'plugin_declaration',name,paths,group,extra=extra)
 for channel in channels:
  label=Path(path).parent.name if project=='hermes' else str(channel)
  dest='agent/channels/'+re.sub('[^a-z0-9_]','_',label.lower())+'.py'
  status='BLOCKED' if label in {'imessage','bluebubbles','qa-channel'} else 'NOT STARTED'
  row=add(project,'channel_integration',label,paths,'G09',status,extra={**extra,'destination_files':[dest,'agent/channels/base.py'],'acceptance_test_files':['tests/channels/test_'+Path(dest).stem+'.py','tests/e2e/test_unified_channel_accounts.py'],'blockers':['Owned service/account/device and permitted credentials are not configured; real target-platform E2E required.']})
  row['acceptance_behavior']+=' Exercise every applicable manifest/config/method capability: pairing/allowlists, groups/topics/threads, streaming edits, attachments/media/reactions, chunking, delivery retry and account isolation; declare unsupported facets individually.'
 for provider in m.get('providers',[]):
  add(project,'model_provider_identity',str(provider),paths,'G13',extra=extra)
# Python register_platform call sites include variants beyond manifest identities (WeCom callback, relay).
root=REPOS['hermes']
for folder in ('plugins','gateway'):
 for path in sorted((root/folder).rglob('*.py')):
  text=path.read_text(encoding='utf8',errors='replace')
  if 'register_platform(' not in text and 'PlatformEntry(' not in text:continue
  tree=ast.parse(text)
  for n in ast.walk(tree):
   if not isinstance(n,ast.Call):continue
   fn=n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else ''
   if fn not in {'register_platform','PlatformEntry'}:continue
   kw={k.arg:k.value for k in n.keywords if k.arg};v=kw.get('name')
   if not isinstance(v,ast.Constant) or not isinstance(v.value,str):continue
   rel=str(path.relative_to(root));dest='agent/channels/'+re.sub('[^a-z0-9_]','_',v.value.lower())+'.py'
   add('hermes','platform_registration',v.value,[rel],'G09',extra={'registration_line':n.lineno,'destination_files':[dest],'acceptance_test_files':['tests/channels/test_'+Path(dest).stem+'.py']})
# Production tool declarations only; do not count test-fixture registrations as product tools.
for item in json.loads((E/'tool-registrations.json').read_text()):
 if not item['path'].startswith(('tools/','plugins/')):continue
 tree=ast.parse((root/item['path']).read_text(encoding='utf8',errors='replace'))
 node=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and n.lineno==item['line'] and isinstance(n.func,ast.Attribute) and n.func.attr=='register')
 name_value=next((k.value for k in node.keywords if k.arg=='name'),None)
 literal=isinstance(name_value,ast.Constant) and isinstance(name_value.value,str)
 name=name_value.value if literal else 'expression registration: '+str(item['declared_name'])
 group='G11' if any(s in name for s in ('browser','computer')) else 'G06' if 'skill' in name else 'G08' if any(s in name for s in ('delegate','kanban')) else 'G05' if any(s in name for s in ('memory','session_search')) else 'G12' if any(s in name for s in ('vision','audio','image','video','speech')) else 'G02'
 add('hermes','tool_declaration',name,[item['path']],group,extra={'registration':item,'literal_name':literal})
# Core toolset names provide separate coverage for table-driven registrations.
tree=ast.parse((root/'toolsets.py').read_text())
for n in tree.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'_HERMES_CORE_TOOLS','_HERMES_WEBHOOK_SAFE_TOOLS','_FEISHU_TOOLS','_YUANBAO_TOOLS'}:
  for name in ast.literal_eval(n.value):
   add('hermes','toolset_member',name,['toolsets.py'],'G03',extra={'toolset_constant':n.targets[0].id})
for item in json.loads((E/'skill-packages.json').read_text()):
 name=item['frontmatter_excerpt'].get('name') or str(Path(item['path']).parent)
 add(item['repository'],'skill_package',name,[item['path']],'G07',extra={'skill_metadata':item['frontmatter_excerpt'],'missing_implementation':'Review/license/sanitize package and validate its actual workflow; prompt text alone is not executable capability.'})
for item in json.loads((E/'documentation-index.json').read_text()):
 name=next((x['title'] for x in item['headings'] if x['title']),Path(item['path']).stem)
 group='G05' if any(s in item['path'] for s in ('memory','context','compression')) else 'G06' if any(s in item['path'] for s in ('curator','learning','training')) else 'G09' if any(s in item['path'] for s in ('channels','integrations')) else 'G14' if any(s in item['path'] for s in ('desktop','mobile','ios','android','tui','dashboard')) else 'G07' if any(s in item['path'] for s in ('plugin','skills','mcp')) else 'G15'
 add(item['repository'],'documentation_surface',name,[item['path']],group,extra={'headings':item['headings'],'missing_implementation':'Documentation coverage anchor: resolve each applicable behavioral claim to its source and acceptance fixture before declaring parity. Do not count this row as a unique implemented feature.'})
for path in sorted((root/'plugin-catalog').glob('*.yaml')):
 m=yaml.safe_load(path.read_text()) or {}
 add('hermes','catalog_reference',str(m.get('name') or path.stem),[str(path.relative_to(root))],'G07','BLOCKED',extra={'external_catalog_metadata':m,'missing_implementation':'External plugin source is not part of the three audited repos; pin/review its source, license, dependencies and real backend before integration.','blockers':['External repository/source/license not inspected; account/OS requirements may also apply.']})
# All documented environment implementations, even when not chosen as defaults.
for name in ('local','docker','ssh','modal','daytona','vercel_sandbox','managed_modal'):
 add('hermes','execution_backend',name,[f'tools/environments/{name}.py'],'G02' if name in {'local','docker'} else 'G11',extra={'reference_trust_note':'Trusted local shell semantics are not a safe default for untrusted Zenith tool execution.'})
# Persist compact, deterministic graph and row formats. No production code emitted.
(E/'group-dependencies.json').write_text(json.dumps(GROUPS,indent=2)+'\n')
(E/'source-citations.json').write_text(json.dumps(CITATIONS,indent=2)+'\n')
(E/'master-feature-matrix.json').write_text(json.dumps(ROWS,ensure_ascii=False,indent=2)+'\n')
fields=['id','reference_project','entry_type','feature_name','source_evidence','sources','configuration_and_dependencies','zenith_main_equivalent','zenith_pr19_equivalent','missing_implementation','integration_strategy','destination_files','security_implications','acceptance_test_files','acceptance_behavior','status','group']
with (R/'MASTER_FEATURE_PARITY_MATRIX.csv').open('w',newline='',encoding='utf-8') as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
 for row in ROWS:
  writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row[k],(dict,list)) else row[k] for k in fields})
summary={'rows':len(ROWS),'by_entry_type':dict(collections.Counter(r['entry_type'] for r in ROWS)),'by_reference':dict(collections.Counter(r['reference_project'] for r in ROWS)),'by_status':dict(collections.Counter(r['status'] for r in ROWS)),'verified_new_parity_features':0,'count_semantics':'Coverage records, not a count of unique capabilities or loaded models. Declarations/docs/toolset overlap intentionally retained and labeled.'}
(E/'catalog-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
