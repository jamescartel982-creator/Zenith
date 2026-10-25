**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

# Source-to-owner mapping

The table below covers manually traced core contracts. Every declaration/integration/skill/catalog/doc coverage record is preserved in the full CSV/JSON. A source owner maps to an existing or proposed Zenith owner, not to an imported second agent.

| ID / reference | Behavior | Exact source owners | Existing main / PR19 | Proposed group |
| --- | --- | --- | --- | --- |
| F00001 / hermes | Autonomous model/tool/result turn loop | run_agent.py; agent/turn_facade.py; agent/conversation_loop.py; agent/turn_tool_round.py | Agent text generation only / Explicit supervised plans; no model-generated calls | G03 |
| F00002 / openclaw | Streamed tool loop and parallel batches | packages/agent-core/src/agent-loop.ts; packages/agent-core/src/agent-loop-tool-execution.ts | Native token streaming / Fixed serial diagnostics; not autonomous batches | G03 |
| F00003 / hermes | Structured plans, todos and response verification | tools/todo_tool.py; agent/conversation_loop.py; agent/turn_finalizer.py | No native autonomous plan loop / No model-generated plan loop | G03 |
| F00004 / hermes | Segmented sequential/parallel tool execution | agent/tool_executor.py; agent/terminal_approval_batch.py | Seven fixed synchronous diagnostics / Explicit plans and cancellation only | G03 |
| F00005 / hermes | Durable session turn admission and liveness | agent/turn_facade.py; agent/turn_facade_lease.py; agent/turn_liveness.py | Account/conversation persistence / Task leases/reconciliation; no autonomous session ownership | G04 |
| F00006 / hermes | Tool error and empty-output recovery | agent/turn_loop_errors.py; agent/turn_empty_response.py | Existing provider errors/deadlines / No autonomous repair cycle | G03 |
| F00007 / hermes | Interrupt, redirect and long-running background work | agent/interrupt_control.py; tools/async_delegation.py; tools/terminal_tool_background.py | Token-stream cancellation / Supervised task cancel; no process/delegation runtime | G04 |
| F00008 / hermes | Provider routing, fallbacks and credential pools | hermes_cli/fallback_config.py; agent/delegation_provider.py; run_agent.py | Registry/orchestration account-scoped text routing / Preserved existing routing; queued hybrid unavailable | G13 |
| F00009 / openclaw | Versioned WebSocket connect and gateway RPC | packages/gateway-protocol/src/schema/frames.ts; src/gateway/server/ws-connection/message-handler.ts | HTTP/SSE only / HTTP/SSE pilot; no OpenClaw protocol | G04 |
| F00010 / openclaw | Gateway lifecycle, ownership and deferred startup | src/gateway/server.ts; src/gateway/server-start.ts | FastAPI application lifecycle / Optional worker lifespan and additive storage | G04 |
| F00011 / hermes | Multi-platform gateway lifecycle and session routing | gateway/run.py; gateway/run_adapters.py; gateway/session.py | Accounts/conversation access only / No external messaging | G09 |
| F00012 / hermes | HTTP/OpenAI-compatible agent API and room authority | gateway/platforms/api_server.py; gateway/platforms/api_server_openai_routes.py; gateway/platforms/api_server_room_grants.py | Zenith-specific chat HTTP/SSE / Supervised task HTTP; no provider API parity | G04 |
| F00013 / hermes | TUI/desktop JSON-RPC backend | tui_gateway/server.py; ui-tui/package.json | Simple terminal CLI and web UI / No TUI/desktop RPC | G14 |
| F00014 / hermes | Bounded curated cross-session MEMORY.md / USER.md | tools/memory_tool.py; tools/memory_tool_store.py | Account-owned explicit SQLite notes / Preserved notes; no automatic memory extraction | G05 |
| F00015 / hermes | Pluggable memory lifecycle and scoped egress | agent/memory_manager.py; agent/memory_provider.py; agent/memory_caller_scope.py | No external memory provider engine / Project retrieval explicitly unavailable | G05 |
| F00016 / hermes | Conversation search with lineage-aware results | tools/session_search_tool.py; hermes_state.py | Conversation listing/history / No cross-session search API | G05 |
| F00017 / openclaw | Scoped hybrid semantic/lexical retrieval | extensions/memory-core/src/memory/manager.ts; extensions/memory-core/src/memory/hybrid.ts | Shared lexical corpus and separate user notes / No scoped embeddings backend | G05 |
| F00018 / hermes | Context compression and durable pre-compression checkpoint | agent/context_compressor.py; agent/conversation_compression.py; agent/conversation_compression_checkpoint.py | Manual account conversation summary / No automatic context checkpoint/compaction engine | G05 |
| F00019 / hermes | Per-conversation stable prompt/tool surfaces | agent/prompt_cache_scope.py; agent/skills_index_delta.py; agent/turn_context.py | Context rebuilt per turn; no measured prefix reuse / Live authorization independent of context | G05 |
| F00020 / hermes | Skills list/view/create/edit/patch/delete | tools/skills_tool.py; tools/skill_manager_tool.py; tools/skill_manager_guards.py | Built-in validated prompt/resource profiles / Same profiles; no generated package activation | G06 |
| F00021 / hermes | Skill usage feedback, ledger and provenance | tools/skill_usage.py; tools/skill_ledger.py; tools/skill_provenance.py | Human-reviewed turn corrections and skill activation records / No candidate skill learning engine | G06 |
| F00022 / hermes | Curator review, consolidation, aging and backups | agent/curator.py; agent/curator_backup.py | No autonomous skill curation / No autonomous skill curation | G06 |
| F00023 / hermes | Third-party skill install and security inspection | tools/skills_hub.py; tools/skills_hub_install.py; tools/skills_guard.py; tools/skills_ast_audit.py | No executable skill package installation / Unavailable | G07 |
| F00024 / hermes | External skill source hubs and synchronization | tools/skills_hub_sources.py; tools/skills_hub_clawhub.py; tools/skills_hub_github.py; tools/skills_sync.py | Reference catalog only / No hub installer | G07 |
| F00025 / hermes | Trajectory and replay data for improvement | hermes_state.py; agent/session_persistence.py; batch_runner.py | Approved native turn export and versioned curriculum / No execution trajectory learning | G06 |
| F00026 / openclaw | Plugin manifest discovery and runtime loading | src/plugins/manifest.ts; src/plugins/discovery.ts; src/plugins/loader-module-runtime.ts | Trusted model transport protocol only / Executable plugins unavailable | G07 |
| F00027 / hermes | Plugin discovery, scoped registration and package validation | hermes_cli/plugins.py; hermes_cli/plugin_validate_private_imports.py; tools/registry.py | No untrusted plugin host / Unavailable | G07 |
| F00028 / hermes | MCP stdio/SSE/streamable HTTP, OAuth and schema discovery | tools/mcp_tool_transport.py; tools/mcp_oauth.py; tools/mcp_tool_registration.py; tools/mcp_schema_cache.py | No MCP client / Unavailable | G07 |
| F00029 / hermes | Subagent leaf/orchestrator roles and strict tool surfaces | tools/delegate_tool.py; tools/delegate_tool_child_run.py; tools/delegate_tool_toolsets.py | Model federation is not subagent execution / No subagent executor | G08 |
| F00030 / hermes | Async delegation, steer/cancel and recovery | tools/async_delegation.py; tools/delegate_tool_registry.py; tools/delegate_tool_dispatch.py | No child task graph / Unavailable | G08 |
| F00031 / openclaw | Subagent spawn and durable registry | src/agents/subagents/spawn/subagent-spawn.ts; src/agents/subagents/registry/subagent-registry.ts | No subagent runtime / Unavailable | G08 |
| F00032 / hermes | Kanban task coordination, review lanes and attachments | hermes_cli/kanban.py; tools/kanban_tools.py | Human-review queue for chat only / No specialist task graph | G08 |
| F00033 / hermes | Skill/worktree-isolated coding agents and editor ACP | acp_adapter/server.py; agent/delegation_backends.py; tools/delegate_tool_config.py | Coding provider routing only / No coding workspace/test runner | G08 |
| F00034 / hermes | Shell/process management with selectable environments | tools/terminal_tool.py; tools/terminal_tool_backends.py; tools/process_registry.py | No general shell / No general shell; sandbox unavailable | G02 |
| F00035 / hermes | Read/write/patch/search files and document extraction | tools/file_tools.py; tools/file_operations.py | Pasted-code offline audit only / No filesystem executor | G02 |
| F00036 / hermes | Programmatic tool execution via Python | tools/code_execution_tool.py | No general Python execution on main / No general code sandbox | G02 |
| F00037 / hermes | Docker execution backend | tools/environments/docker.py; tools/environments/docker_egress.py | Application Docker packaging only / No code sandbox | G02 |
| F00038 / hermes | SSH remote execution and file synchronization | tools/environments/ssh.py; tools/environments/file_sync.py | No remote execution / Unavailable | G11 |
| F00039 / hermes | Modal, Daytona and Vercel execution | tools/environments/modal.py; tools/environments/daytona.py; tools/environments/vercel_sandbox.py | No remote execution services / Unavailable | G11 |
| F00040 / hermes | CDP browser automation, dialogs and session lifecycle | tools/browser_use_cli.py; tools/browser_cdp_tool.py; tools/browser_dialog_tool.py; tools/browser_session.py | browser.py only opens chat page / Browser automation unavailable | G11 |
| F00041 / hermes | Browser vault origin-bound credential handles | tools/browser_vault_tool.py; tools/browser_vault_context.py | No credential-fill tool / Unavailable | G11 |
| F00042 / hermes | Computer input/capture with permission mediation | tools/computer_use/tool.py; tools/computer_use/permissions.py; tools/computer_use/cua_backend.py | No computer control / Unavailable | G11 |
| F00043 / openclaw | Browser auth, SSRF policy and privileged profile import | extensions/browser/src/browser-tool.ts; extensions/browser/src/browser/ssrf-policy-helpers.ts | No browser control / Unavailable; host-profile import not adopted by default | G11 |
| F00044 / openclaw | Computer interaction transport | src/agents/tools/computer-tool.ts | No computer tool / Unavailable | G11 |
| F00045 / hermes | Vision input normalization and history budgets | tools/vision_tools.py; tools/vision_tools_image_prep.py; tools/vision_tools_history_budget.py | Catalog metadata is not a multimodal engine / Text-only executor | G12 |
| F00046 / hermes | Image and video generation providers | tools/image_generation_tool.py; tools/image_generation_catalog.py | No generation engine / Unavailable | G12 |
| F00047 / hermes | Audio containers, transcription and voice delivery | tools/audio_container.py; tools/transcription_audio.py; gateway/platforms/base_streaming_tts.py | No audio pipeline / Unavailable | G12 |
| F00048 / hermes | Browser preview and desktop display tools | tools/read_terminal_tool.py; tools/annotate_preview_tool.py; tools/computer_use/tool.py | No desktop preview / Unavailable | G14 |
| F00049 / hermes | Cron/interval scheduling and delivery | cron/jobs.py; cron/scheduler.py; gateway/platforms/send_targets.py | CI diagnostic cron is not per-user scheduling / Unavailable | G10 |
| F00050 / openclaw | Durable scheduler admission and authority | src/cron/service.ts; src/cron/store.ts; src/cron/run-authority.ts | No user scheduler / Unavailable | G10 |
| F00051 / openclaw | Channel ingress durable claims and events | src/channels/message/ingress-drain.ts; src/infra/agent-events.ts | No channel ingress / Task events only; no external delivery | G09 |
| F00052 / hermes | Webhook ingress, event routing and replay boundaries | gateway/platforms/webhook.py; gateway/platforms/webhook_ingress.py; gateway/platforms/access_policy_mixin.py | No external webhook surface / Unavailable | G09 |
| F00053 / hermes | Trust-scoped tool search and deferred schemas | tools/tool_search.py; tools/registry.py; model_tools.py | Static fixed tool list; provider discovery separate / Fixed seven-tool registry, no semantic tool discovery | G07 |
| F00054 / hermes | Profile-aware configuration and context propagation | hermes_constants.py; gateway/platform_registry.py; agent/memory_provider.py | Account/session isolation; env Settings / Server-derived ActorContext, not Hermes profiles | G01 |
| F00055 / openclaw | Operator scopes and current run authority | src/gateway/operator-scopes.ts; src/agents/admitted-run-context.ts; src/agents/agent-tools.turn-authority.ts | Owner/MFA/fixed capability grants / Live session/revision and exact action approvals | G01 |
| F00056 / hermes | Child environment secret scrubbing | tools/environments/local_env_policy.py; tools/environments/local.py; agent/redact.py | Owner-secret prompt guards / Redaction/canaries; no untrusted process environment yet | G01 |
| F00057 / openclaw | External-content boundaries and audit metadata | src/security/external-content.ts; src/audit/audit-event-store.ts | Guarded prompts and local execution audit / Metadata HMAC history, not root-proof ledger | G01 |
| F00058 / hermes | CLI slash commands and interactive session controls | cli.py; hermes_cli/main.py | Existing zenith terminal commands / Same CLI; no full TUI parity | G14 |
| F00059 / hermes | Web dashboard and file/terminal UI | hermes_cli/web_server.py; web/package.json | Current plain-JS chat/admin/memory UI / No new task dashboard panels | G14 |
| F00060 / hermes | Electron desktop and SSH runtime management | apps/desktop/package.json; hermes_cli/windows_ssh_runtime.py | No desktop companion / No desktop companion | G14 |
| F00061 / openclaw | Native macOS/iOS/Android companion applications | apps/macos/Package.swift; apps/ios/project.yml; apps/android/build.gradle.kts | Web interface only / No native companions | G14 |
| F00062 / hermes | Packaging, updater and managed Python runtime | pm/pyproject.toml; pm/environments.py; hermes_cli/update_cmd.py; hermes_cli/subcommands/update.py | Windows/Linux pip/venv local install / Install remains unchanged; no Hermes PM adoption | G15 |
| F00063 / hermes | Observability, tracing and accounting | hermes_cli/observability/relay_shared_metrics.py; agent/aux_accounting.py | Bounded local generation metrics / Task metadata audit and existing metrics only | G15 |
| F00064 / hermes | Mixture-of-agents alternation, synthesis and trace | agent/moa_loop.py; agent/moa_alternation.py; agent/moa_trace.py | Existing model federation/review/synthesis / Preserved federation; not specialist execution | G13 |
| F00065 / hermes | Voice conversation, interruption and wake engines | tools/voice_mode.py; tools/voice_live.py; tools/wake_word.py; tools/wake_word_engines.py | Text only / Unavailable | G12 |
| F00066 / hermes | Local/remote streaming TTS and speaker routing | tools/tts_tool.py; tools/tts_streaming.py; tools/tts_tool_local.py | No speech / Unavailable | G12 |
| F00067 / hermes | Video generation and media workflows | tools/video_generation_tool.py; tools/xai_video_tools.py | No media executor / Unavailable | G12 |
| F00068 / hermes | Source retrieval and bounded web extraction | tools/web_tools.py; tools/web_tools_extract.py; tools/web_tools_rescue.py | Local source-linked lexical excerpts only / No live research executor | G13 |
| F00069 / hermes | Goals, personality and per-session context policy | hermes_cli/goals.py; hermes_cli/personality.py; agent/conversation_loop.py | Prompt profiles, personal notes and summaries / Existing behavior preserved | G14 |
| F00070 / hermes | Hooks and event-driven outbound integration | agent/shell_hooks.py; agent/outbound_webhooks.py; hermes_cli/hooks.py | No untrusted hook executor / Unavailable | G10 |
| F00071 / hermes | Write-approval staging and skill mutation gates | tools/write_approval.py; tools/skill_manager_tool.py | Owner/MFA capability grants / Exact diagnostic approvals; no skill mutation | G01 |
| F00072 / hermes | Language packs and localized interfaces | agent/i18n_languages.py; hermes_cli/config_language.py | Existing English UI / No localization package registry | G14 |

Specific channel/provider identities share canonical owners only when protocol behavior is compatible. Source-specific modes and acceptance facets remain separate. File-plan records flag overlaps with the still-unmerged PR18 and PR19; reconciliation is required before editing.
