# File-by-file implementation plan

Pinned source: `fcec8993b068cc72f2ca918a8ef5680dbc9b2255`. Status describes current source, not a promise of deployment or full capability verification.

**Proposal only.** Destination modules/tests not present at the pinned commit are future files, not placeholder implementations. Existing owners and APIs remain authoritative. Complexity: M = roughly 4–8 engineering days, L = 2–4 engineering weeks, XL = 4–8+ weeks including integration/validation. Estimates are per capability and overlap; they are not delivery guarantees. External access, hardware, OS consent and review can block completion.

Prerequisite IDs form an acyclic implementation graph. Existing implementations may be reused immediately; a specialist remains unavailable until its own backend acceptance passes. Add schema versions in component-specific namespaces in the same Store database; **never rewrite the existing platform v1 SCHEMA/CHECKSUM** or legacy table layouts. Every migration needs a reviewed backup/restore test and explicit owner approval before production application.

## 1. Advanced reasoning

Current: **PARTIAL**. Milestone: **M3**. Complexity: **L**. Prerequisites: 2, 8, 10.

- Reuse: [agent/reasoning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/reasoning.py); [agent/planning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/planning.py); [agent/verification.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/verification.py).
- Destination files: `agent/plan_graph.py`, `agent/reasoning.py`.
- Work and expected behavior: Add hierarchical constraint-bearing task graphs, hypothesis/evidence tracking and code/document/structured-data plans; keep call, token and deadline budgets.
- Tests: `tests/test_reasoning.py`, `tests/test_plan_graph.py`.
- Acceptance: Dependency-valid plans terminate within budget; contradictory constraints and unsupported conclusions fail verification; compare native versus engine on frozen tasks.
- Security/integration risk: Model suggestions must never authorize execution.
- Configuration: `ZENITH_PLAN_GRAPH_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 2. Self-reflection and verification

Current: **PARTIAL**. Milestone: **M2**. Complexity: **M**. Prerequisites: 8.

- Reuse: [agent/response_verifier.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/response_verifier.py); [agent/verification.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/verification.py); [agent/reasoning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/reasoning.py).
- Destination files: `agent/claim_verifier.py`, `agent/reasoning.py`.
- Work and expected behavior: Persist claim/evidence checks and failure reasons, classify retryable failures, request missing evidence, and distinguish model opinion from independent validation.
- Tests: `tests/test_claim_verifier.py`, `tests/test_reasoning.py`.
- Acceptance: Unsupported claims stay unverified; false citations fail; bounded retry stops; evaluation records reproduce the decision.
- Security/integration risk: Self-review may reinforce an incorrect answer; avoid self-scored confidence.
- Configuration: `ZENITH_CLAIM_VERIFICATION_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 3. Persistent memory

Current: **PARTIAL**. Milestone: **M2**. Complexity: **L**. Prerequisites: 8.

- Reuse: [agent/personal.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/personal.py); [agent/storage.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/storage.py); [agent/summaries.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/summaries.py); [agent/platform_migrations.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/platform_migrations.py).
- Destination files: `agent/project_memory.py`, `agent/semantic_memory.py`, `agent/project_memory_migrations.py`, `agent/platform_config.py`, `agent/core.py`, `agent/memory_gateway.py`.
- Work and expected behavior: Add account/project-scoped episodic and semantic retrieval, consolidation, retention/expiration/deletion and optional separately versioned embedding index in the existing SQLite owner.
- Tests: `tests/test_project_memory.py`, `tests/test_semantic_memory.py`, `tests/test_personal.py`.
- Acceptance: Identical documents in different owners/projects never cross scopes; deletion removes index entries; held-out recall and factual consistency exceed frozen lexical baseline.
- Security/integration risk: Cross-account leakage and persistence/deletion consistency; no automatic memory merging.
- Configuration: `ZENITH_PLATFORM_MEMORY_ENABLED (currently rejected; enable only after acceptance)` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 4. Long-context intelligence

Current: **PARTIAL**. Milestone: **M2**. Complexity: **L**. Prerequisites: 3, 18, 32.

- Reuse: [agent/core.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/core.py); [agent/providers.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/providers.py); [agent/storage.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/storage.py); [agent/summaries.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/summaries.py).
- Destination files: `agent/repository_index.py`, `agent/context_manager.py`, `agent/document_index.py`, `agent/core.py`.
- Work and expected behavior: Add repository/document indexing, source-linked hierarchical summaries, retrieval ranking and context-budget allocation without changing tokenizer or architectural limits.
- Tests: `tests/test_repository_index.py`, `tests/test_context_manager.py`.
- Acceptance: Retrieval spans retain file/page hashes and owners; budget never overflows; multi-document answers cite retrieved spans and report contradictions.
- Security/integration risk: Summary errors and source injection; compression is not an architectural context extension.
- Configuration: `ZENITH_CONTEXT_INDEX_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 5. Dynamic model routing

Current: **EXISTING**. Milestone: **M2**. Complexity: **M**. Prerequisites: 8.

- Reuse: [agent/model_registry.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_registry.py); [agent/task_router.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/task_router.py); [agent/orchestration.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/orchestration.py); [agent/provider_adapters/local_adapter.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/provider_adapters/local_adapter.py).
- Destination files: `agent/routing_metrics.py`, `agent/task_router.py`, `agent/model_registry.py`.
- Work and expected behavior: Persist trustworthy routing measurements, add workload cohorts and validate live provider accounts where credentials exist; preserve existing text-only contracts.
- Tests: `tests/test_model_registry.py`, `tests/test_orchestration.py`, `tests/test_routing_metrics.py`.
- Acceptance: Local-only emits zero external calls; inaccessible models remain unavailable; quality/cost/context constraints are obeyed under fallback.
- Security/integration risk: Provider output rights, privacy, stale access and unknown pricing; API keys do not grant universal model access.
- Configuration: `Existing AI_PROVIDER / ZENITH_ALLOW_EXTERNAL, new ZENITH_ROUTING_METRICS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 6. Knowledge graph

Current: **MISSING**. Milestone: **M5**. Complexity: **L**. Prerequisites: 3, 4, 18, 32.

- Reuse: [agent/storage.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/storage.py).
- Destination files: `agent/knowledge_graph.py`, `agent/graph_retrieval.py`, `agent/graph_migrations.py`.
- Work and expected behavior: Add scoped entities, relations, evidence spans, temporal versions, dependency edges and contradiction records; extracted assertions remain proposals until source validation.
- Tests: `tests/test_knowledge_graph.py`, `tests/test_graph_retrieval.py`.
- Acceptance: Every edge traces to a real versioned source; conflicting assertions remain visible; deletion cascades logically and scope filters survive adversarial queries.
- Security/integration risk: False relations and cross-project joins; model extraction is not ground truth.
- Configuration: `ZENITH_KNOWLEDGE_GRAPH_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 7. Adaptive learning

Current: **PARTIAL**. Milestone: **M1**. Complexity: **L**. Prerequisites: 8.

- Reuse: [agent/learning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/learning.py); [agent/curriculum.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/curriculum.py); [agent/continual.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/continual.py); [agent/stabilize.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/stabilize.py); [agent/deployment.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/deployment.py).
- Destination files: `agent/evolution/observer.py`, `agent/evolution/discovery.py`, `agent/evolution/proposals.py`, `agent/curriculum.py`.
- Work and expected behavior: Connect feedback/failure analysis to the proposed Evolution Engine; version prompt/workflow/routing experiments and curate candidate datasets with opt-in rights.
- Tests: `tests/test_evolution_observer.py`, `tests/test_evolution_discovery.py`, `tests/test_continuation.py`.
- Acceptance: No feedback alone changes production; repeated failure signatures generate bounded evidence-backed proposals; held-out data never enters replay/training.
- Security/integration risk: Test leakage, proprietary-output training and catastrophic forgetting.
- Configuration: `ZENITH_EVOLUTION_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 8. Uncertainty estimation

Current: **PARTIAL**. Milestone: **M0**. Complexity: **M**. Prerequisites: existing foundation only.

- Reuse: [agent/assurance.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/assurance.py); [agent/quality.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/quality.py); [agent/verification.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/verification.py); [agent/personal.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/personal.py).
- Destination files: `agent/quality.py`, `agent/evidence_sufficiency.py`, `agent/evaluation/suite-v2.json`.
- Work and expected behavior: Repair/version diagnostic scorers, add independent evidence sufficiency and source reliability checks, confidence validation under distribution shift and failed-verification escalation.
- Tests: `tests/test_quality_admin.py`, `tests/test_evidence_sufficiency.py`.
- Acceptance: Plural units and semantic JSON are graded by declared intent; exact-byte tasks remain strict; calibration uses disjoint validation and reports sample counts/uncertainty.
- Security/integration risk: Bad graders produce misleading calibration; citation membership is not entailment.
- Configuration: `Existing ZENITH_CALIBRATION_FILE plus ZENITH_EVIDENCE_CHECKS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 9. Multi-agent orchestration

Current: **PARTIAL**. Milestone: **M3**. Complexity: **XL**. Prerequisites: 10, 13, 15, 16.

- Reuse: [agent/ensemble.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/ensemble.py); [agent/model_federation.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_federation.py); [agent/runtime.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/runtime.py); [integrations/runtime_bridge/src/zenith_integrations/shared/router.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/integrations/runtime_bridge/src/zenith_integrations/shared/router.py).
- Destination files: `agent/supervisor.py`, `agent/agent_registry.py`, `agent/task_graph.py`, `agent/tool_loop.py`, `agent/research_agent.py`, `agent/research_fetch.py`, `agent/source_verifier.py`, `agent/citation_manager.py`, `agent/data_analysis.py`, `agent/infrastructure_tools.py`.
- Work and expected behavior: Add a server-owned specialist registry and supervisor with typed tasks, ownership, isolated capabilities, bounded delegation and provenance. Register each requested specialist only after its real backend works.
- Tests: `tests/test_supervisor.py`, `tests/test_agent_registry.py`.
- Acceptance: All 12 specialist categories have separate acceptance rows; each delegated result is validated; no child gains parent/owner capabilities implicitly.
- Security/integration risk: Delegation must not amplify permissions, recursively spawn indefinitely or duplicate effects.
- Configuration: `ZENITH_SUPERVISOR_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 10. Autonomous task planning

Current: **PARTIAL**. Milestone: **M3**. Complexity: **L**. Prerequisites: 2, 16.

- Reuse: [agent/planning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/planning.py); [agent/task_store.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/task_store.py); [agent/runtime.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/runtime.py).
- Destination files: `agent/task_graph.py`, `agent/planning.py`, `agent/task_store.py`.
- Work and expected behavior: Add versioned DAGs with dependencies, priority, explicit constraints, per-node budgets, durable checkpoints and completion contracts.
- Tests: `tests/test_task_graph.py`, `tests/test_platform_tasks.py`.
- Acceptance: Cycles/invalid dependencies are rejected; progress survives restart; task completion requires explicit checks and renewed authorization at execution.
- Security/integration risk: Cyclic plans, unbounded goals and unsafe replay after uncertain effects.
- Configuration: `ZENITH_TASK_GRAPHS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 11. Browser automation

Current: **MISSING**. Milestone: **M4**. Complexity: **XL**. Prerequisites: 13, 20, 39.

- Reuse: [agent/browser.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/browser.py).
- Destination files: `integrations/browser_service/pyproject.toml`, `integrations/browser_service/src/zenith_browser_service/server.py`, `agent/browser_tools.py`.
- Work and expected behavior: Add an independently sandboxed browser service with navigation/extraction/download bounds and approved forms. Preserve native OpenClaw browser as an explicitly selected future backend, not silently enabled.
- Tests: `integrations/browser_service/tests/test_navigation.py`, `integrations/browser_service/tests/test_injection.py`.
- Acceptance: Real browser fixture tests navigation/forms/downloads; redirects/private addresses and injected permissions are blocked; consequential actions require exact approval.
- Security/integration risk: SSRF, malicious page instructions, credential extraction, downloads and consequential form submission.
- Configuration: `ZENITH_BROWSER_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 12. Computer control

Current: **MISSING**. Milestone: **M7**. Complexity: **XL**. Prerequisites: 11, 20, 29.

- Reuse: existing Store, authentication and execution boundaries.
- Destination files: `integrations/desktop_service/src/zenith_desktop_service/server.py`, `agent/desktop_tools.py`.
- Work and expected behavior: Add opt-in OS-specific desktop brokers for screenshots and constrained application input. Keep upstream companion/device functionality independent and report platform gaps.
- Tests: `integrations/desktop_service/tests/test_permissions.py`, `integrations/desktop_service/tests/test_workflows.py`.
- Acceptance: Supported OS application fixture completes with approval; secure fields/system elevation blocked; unapproved input never occurs; cancellation/recovery retains receipts.
- Security/integration risk: OS privileges, screen secrets, incorrect targets, irreversible UI actions; macOS TCC and Windows/Wayland limitations.
- Configuration: `ZENITH_DESKTOP_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 13. Terminal execution

Current: **PARTIAL**. Milestone: **M3**. Complexity: **L**. Prerequisites: 20.

- Reuse: [agent/execution.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/execution.py); [agent/restricted_python.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/restricted_python.py); [agent/sandbox.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/sandbox.py); [agent/sandbox_docker.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/sandbox_docker.py).
- Destination files: `agent/terminal_tools.py`, `agent/sandbox_docker.py`, `agent/execution.py`, `agent/tool_protocol.py`, `agent/tool_registry.py`.
- Work and expected behavior: Add structured sandbox command tools, environment inspection, reviewed offline dependency installation and bounded development commands; never expose unrestricted shell.
- Tests: `tests/test_terminal_tools.py`, `tests/test_unified_sandbox.py`.
- Acceptance: Real approved container enforces CPU/RAM/PID/time/output quotas, read-only source snapshots and no network; forbidden commands/packages fail before execution.
- Security/integration risk: Commands, package build hooks and test code are untrusted execution; no host fallback or inherited secrets.
- Configuration: `ZENITH_TERMINAL_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 14. Scheduled automation

Current: **PARTIAL**. Milestone: **M4**. Complexity: **L**. Prerequisites: 10, 15, 16.

- Reuse: [.github/workflows/evaluation.yml](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/.github/workflows/evaluation.yml); [deploy/four_system/services.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/deploy/four_system/services.py); [agent/event_bus.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/event_bus.py).
- Destination files: `agent/scheduler.py`, `agent/outbox.py`, `agent/scheduler_migrations.py`.
- Work and expected behavior: Add durable schedules, event conditions, bounded retries and approved outbox delivery. Use revocable schedule-specific authority, never expired owner cookies.
- Tests: `tests/test_scheduler.py`, `tests/test_outbox.py`.
- Acceptance: Clock/restart tests execute due tasks once; unauthorized/expired actions wait; delivery uses stable receipts and actual configured channels.
- Security/integration risk: Duplicate deliveries, stale permissions and effect replay; actions outside active authorization must wait for review.
- Configuration: `ZENITH_SCHEDULER_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 15. Agent collaboration

Current: **PARTIAL**. Milestone: **M3**. Complexity: **L**. Prerequisites: 2, 10, 16.

- Reuse: [agent/ensemble.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/ensemble.py); [agent/model_federation.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_federation.py); [agent/event_bus.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/event_bus.py).
- Destination files: `agent/collaboration.py`, `agent/task_artifacts.py`.
- Work and expected behavior: Add typed messages, scoped artifact handles, conflict records and independent result validation; preserve native runtime session ownership.
- Tests: `tests/test_collaboration.py`, `tests/test_task_artifacts.py`.
- Acceptance: Cross-owner/project messages fail; artifacts are hash-addressed; contradictory results escalate; same effect cannot be committed by two specialists.
- Security/integration risk: Private data crossing agents/providers, permission laundering and duplicated external actions.
- Configuration: `ZENITH_AGENT_COLLABORATION_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 16. Failure recovery

Current: **PARTIAL**. Milestone: **M1**. Complexity: **L**. Prerequisites: existing foundation only.

- Reuse: [agent/task_store.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/task_store.py); [agent/runtime.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/runtime.py); [integrations/runtime_bridge/src/zenith_integrations/shared/ledger.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/integrations/runtime_bridge/src/zenith_integrations/shared/ledger.py).
- Destination files: `agent/recovery.py`, `agent/task_store.py`, `agent/task_graph.py`.
- Work and expected behavior: Add classified pure-operation retries and resumable DAG checkpoints; retain manual reconciliation for unknown effects and tested rollback handlers for reversible operations.
- Tests: `tests/test_recovery.py`, `tests/test_platform_tasks.py`.
- Acceptance: Kill/restart/cancel at every admission/effect/receipt boundary; pure retries stay bounded; uncertain effects remain blocked for human reconciliation.
- Security/integration risk: Exactly-once effects cannot be assumed after a network/process failure.
- Configuration: `ZENITH_RECOVERY_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 17. Autonomous coding agent

Current: **MISSING**. Milestone: **M3**. Complexity: **XL**. Prerequisites: 13, 18, 19, 20.

- Reuse: [agent/verification.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/verification.py); [agent/tools.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/tools.py).
- Destination files: `agent/coding_agent.py`, `agent/patch_manager.py`, `agent/test_runner.py`, `agent/task_checkpoint.py`.
- Work and expected behavior: Add sandboxed analyze/propose/patch/test/review workflow, code generation/debug/refactor and resumable task state. Produce reviewable diffs instead of committing automatically.
- Tests: `tests/test_coding_agent.py`, `tests/test_patch_manager.py`, `tests/integration/test_repository_fixes.py`.
- Acceptance: Real small-repo bugs are fixed and hidden tests pass; unrelated behavior retained; patch paths/symlinks rejected; no silent commit/push.
- Security/integration risk: Repository tests and patches can execute arbitrary code or modify protected files.
- Configuration: `ZENITH_CODING_AGENT_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 18. Repository intelligence

Current: **MISSING**. Milestone: **M2**. Complexity: **L**. Prerequisites: existing foundation only.

- Reuse: [agent/platform_repository.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/platform_repository.py).
- Destination files: `agent/repository_index.py`, `agent/repository_analysis.py`.
- Work and expected behavior: Add bounded complete-repository source inventory, syntax/symbol/import/dependency indexing, impact analysis and architecture change tracking with evidence links.
- Tests: `tests/test_repository_index.py`, `tests/test_repository_analysis.py`.
- Acceptance: Index a frozen multi-language fixture without executing it; resolve supported imports/symbols, report uncertainty and identify affected files reproducibly.
- Security/integration risk: Untrusted files, symlink/path traversal, generated/vendor code and parser resource exhaustion.
- Configuration: `ZENITH_REPOSITORY_INDEX_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 19. Multi-language programming

Current: **PARTIAL**. Milestone: **M3**. Complexity: **XL**. Prerequisites: 13, 18, 20.

- Reuse: [agent/tools.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/tools.py); [agent/verification.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/verification.py).
- Destination files: `agent/language_tools.py`, `integrations/devtools/`.
- Work and expected behavior: Add explicit language-toolchain adapters for Python/JS/TS/Rust/Go/C++/Java/SQL/Bash with pinned compilers or LSPs inside the sandbox, one verified platform/backend at a time.
- Tests: `tests/test_language_tools.py`, `tests/integration/test_language_toolchains.py`.
- Acceptance: Each language compiles/lints/tests a real fixture; missing toolchains report blocked; no host package installs or network fallback.
- Security/integration risk: Toolchain availability and platform-specific licensing/build hooks; text generation is not verified language mastery.
- Configuration: `ZENITH_LANGUAGE_TOOLS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 20. Sandboxed code execution

Current: **PARTIAL**. Milestone: **M1**. Complexity: **L**. Prerequisites: existing foundation only.

- Reuse: [agent/sandbox.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/sandbox.py); [agent/sandbox_docker.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/sandbox_docker.py); [scripts/smoke_sandbox.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/scripts/smoke_sandbox.py).
- Destination files: `agent/sandbox_workspace.py`, `agent/sandbox_docker.py`, `agent/execution.py`, `agent/tool_protocol.py`.
- Work and expected behavior: Extend to immutable workspace snapshots and explicit command/toolchain adapters; verify egress and artifact extraction. Use VM isolation for hostile malware, not this container.
- Tests: `tests/test_sandbox_workspace.py`, `tests/test_unified_sandbox.py`, `scripts/smoke_sandbox.py`.
- Acceptance: Actual containment probes enforce limits and no host secrets/mounts/network; cancellation and cleanup confirmed; failed backend never falls back to host execution.
- Security/integration risk: Containers share the host kernel; Docker daemon/image remain trusted; no universal escape-resistance claim.
- Configuration: `Existing ZENITH_SANDBOX_ENABLED plus ZENITH_SANDBOX_WORKSPACES_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 21. GitHub integration

Current: **PARTIAL**. Milestone: **M4**. Complexity: **L**. Prerequisites: 13, 17, 20.

- Reuse: [agent/discovery.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/discovery.py); [agent/registry.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/registry.py).
- Destination files: `agent/github_client.py`, `agent/github_tools.py`.
- Work and expected behavior: Add repository-scoped GitHub read/review and draft-PR integration using secret handles and exact revision approvals for writes/merges.
- Tests: `tests/test_github_client.py`, `tests/integration/test_github_workflow.py`.
- Acceptance: Real test-repository read/branch/draft-PR workflow with explicit approval; expected-head checks prevent stale merge; tokens never enter prompts/logs.
- Security/integration risk: Overbroad tokens, untrusted issue text, branch races and unintended publishing.
- Configuration: `ZENITH_GITHUB_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 22. Software architecture agent

Current: **MISSING**. Milestone: **M3**. Complexity: **L**. Prerequisites: 9, 18, 19.

- Reuse: [agent/planning.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/planning.py).
- Destination files: `agent/architecture_analysis.py`, `agent/agent_registry.py`.
- Work and expected behavior: Add API/dependency/schema/IaC analysis, design proposals and evidence-linked architecture reports as a scoped supervisor specialist.
- Tests: `tests/test_architecture_analysis.py`.
- Acceptance: Reports cite actual modules/configuration and label hypotheses; proposed API/schema changes include compatibility tests and rollback.
- Security/integration risk: Generated designs may ignore deployment constraints or propose unsafe migrations.
- Configuration: `ZENITH_ARCHITECTURE_AGENT_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 23. Security operations agent

Current: **MISSING**. Milestone: **M5**. Complexity: **L**. Prerequisites: 3, 8, 9.

- Reuse: [agent/monitoring.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/monitoring.py).
- Destination files: `agent/security/operations.py`, `agent/security/logs.py`.
- Work and expected behavior: Add offline structured log ingestion, event normalization/correlation, triage/anomaly scoring and optional approved SIEM read adapters.
- Tests: `tests/security/test_operations.py`, `tests/security/test_log_injection.py`.
- Acceptance: Labeled benign/attack log fixtures measure detection and false-positive rate; sources/timestamps retained; logs cannot authorize tools.
- Security/integration risk: Sensitive logs, false positives and injected log instructions; no automatic containment.
- Configuration: `ZENITH_SECURITY_OPERATIONS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 24. Vulnerability analysis

Current: **PARTIAL**. Milestone: **M0 / M5**. Complexity: **L**. Prerequisites: 8, 18, 20.

- Reuse: [agent/tools.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/tools.py); [scripts/audit_dependencies.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/scripts/audit_dependencies.py); [.github/workflows/security.yml](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/.github/workflows/security.yml).
- Destination files: `scripts/audit_dependencies.py`, `agent/security/vulnerabilities.py`, `.github/workflows/security.yml`.
- Work and expected behavior: Harden advisory coverage, add pinned SAST and configuration adapters, correlate source evidence and remediation; verify authorized fixes in isolated fixtures.
- Tests: `tests/test_dependency_audit.py`, `tests/security/test_vulnerabilities.py`.
- Acceptance: Unscanned packages cannot silently produce a complete-audit result; known vulnerable fixtures detected; remediation tests pass without unauthorized network activity.
- Security/integration risk: Advisory skips, false positives, untrusted repositories and exploit validation outside scope.
- Configuration: `ZENITH_VULNERABILITY_ANALYSIS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 25. Malware analysis sandbox

Current: **MISSING**. Milestone: **M5 / M7**. Complexity: **XL**. Prerequisites: 20, 23, 26.

- Reuse: existing Store, authentication and execution boundaries.
- Destination files: `integrations/malware_lab/`, `agent/security/malware.py`.
- Work and expected behavior: Start with bounded static inspection and reports. Dynamic malware execution requires a separate disposable VM/microVM lab, controlled samples and verified isolation before activation.
- Tests: `tests/security/test_malware_static.py`, `integrations/malware_lab/tests/test_isolation.py`.
- Acceptance: Static benign test samples produce hash/IOC evidence without execution; real dynamic-lab containment is independently reviewed; no malware deployed to third parties.
- Security/integration risk: Actual hostile code, sensitive artifacts, network escape and destructive side effects; blocked without stronger lab infrastructure.
- Configuration: `ZENITH_MALWARE_STATIC_ENABLED; dynamic lab separately disabled` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 26. Threat intelligence

Current: **MISSING**. Milestone: **M5**. Complexity: **L**. Prerequisites: 3, 6, 23, 24.

- Reuse: [agent/resources/sources-v1.json](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/resources/sources-v1.json).
- Destination files: `agent/security/threat_intel.py`, `agent/security/feeds.py`.
- Work and expected behavior: Add licensed versioned feed ingestion, CVE/vendor/ATT&CK mapping, IOC enrichment and campaign reports with timestamps and attribution.
- Tests: `tests/security/test_threat_intel.py`.
- Acceptance: Known dated feed fixtures map correctly; every factual claim cites actual retrieved records; stale/contradictory intelligence remains explicit.
- Security/integration risk: Stale or malicious feeds and unsupported attribution; no automatic external scans/blocking.
- Configuration: `ZENITH_THREAT_INTEL_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 27. Authorized penetration testing

Current: **PARTIAL**. Milestone: **M5**. Complexity: **XL**. Prerequisites: 9, 20, 24.

- Reuse: [agent/execution.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/execution.py); [agent/skill_access.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/skill_access.py).
- Destination files: `agent/security/assessment.py`, `agent/tool_registry.py`.
- Work and expected behavior: Add strictly scoped lab assessment plans, approved configuration tests, vulnerability/remediation validation and reports through existing execution controls.
- Tests: `tests/security/test_assessment_scope.py`, `tests/security/test_lab_assessment.py`.
- Acceptance: Allowlisted lab only; out-of-scope IP/ports denied before traffic; cancellation/revocation/approval audited; no unauthorized intrusion, credential theft or destructive tooling.
- Security/integration risk: Unauthorized targets, privilege amplification and destructive activity; lab/authorization references required.
- Configuration: `ZENITH_LAB_ASSESSMENT_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 28. Incident response

Current: **MISSING**. Milestone: **M5**. Complexity: **L**. Prerequisites: 3, 23, 26.

- Reuse: [agent/resources/skills-v1.json](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/resources/skills-v1.json).
- Destination files: `agent/security/incident_response.py`, `agent/security/evidence.py`.
- Work and expected behavior: Add evidence hashes, forensic artifact parsing, event timelines, root-cause hypotheses and containment/recovery plans with human-approved actions.
- Tests: `tests/security/test_incident_response.py`.
- Acceptance: Timeline reconstructed from a known incident fixture; provenance survives export; hypotheses labeled; containment never runs without separate authority.
- Security/integration risk: Evidence contamination, private data disclosure and irreversible containment changes.
- Configuration: `ZENITH_INCIDENT_RESPONSE_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 29. Vision engine

Current: **MISSING**. Milestone: **M6**. Complexity: **XL**. Prerequisites: 8, 32, 37.

- Reuse: [agent/model_packs/zenith-vision.json](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_packs/zenith-vision.json); [integrations/inference_service/src/zenith_inference/chat_contract.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/integrations/inference_service/src/zenith_inference/chat_contract.py).
- Destination files: `agent/multimodal/vision.py`, `agent/multimodal/ocr.py`.
- Work and expected behavior: Add optional compatible vision/OCR adapters for images/screenshots/charts/VQA, with bounded inputs and explicit external-data consent. Keep vision weights separate from Zenith's preserved text model.
- Tests: `tests/multimodal/test_vision.py`, `tests/multimodal/test_ocr.py`.
- Acceptance: Actual configured model/OCR processes a frozen image set; accuracy and chart/VQA limits reported; text-only install still works without dependencies.
- Security/integration risk: Image secrets, parser exploits and hallucinated visual details; no arbitrary embedding compatibility assumptions.
- Configuration: `ZENITH_VISION_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 30. Speech intelligence

Current: **MISSING**. Milestone: **M6**. Complexity: **XL**. Prerequisites: 8, 37.

- Reuse: existing Store, authentication and execution boundaries.
- Destination files: `agent/multimodal/audio.py`, `agent/multimodal/speech.py`.
- Work and expected behavior: Add optional local/authorized STT and TTS, transcription and multilingual adapters, with separate explicit consent for speaker processing and retained audio.
- Tests: `tests/multimodal/test_audio.py`, `tests/multimodal/test_speech.py`.
- Acceptance: Real frozen clips measure word-error rate and TTS intelligibility/latency; absent backends fail clearly; authorized speaker features tested separately.
- Security/integration risk: Audio privacy, voice rights, biometric consent and optional native dependency availability.
- Configuration: `ZENITH_AUDIO_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 31. Real-time voice assistant

Current: **MISSING**. Milestone: **M7**. Complexity: **XL**. Prerequisites: 9, 16, 30.

- Reuse: existing Store, authentication and execution boundaries.
- Destination files: `agent/voice_session.py`, `agent/voice_gateway.py`.
- Work and expected behavior: Add authenticated voice sessions, audio buffers/VAD/turn state, streaming transcription/playback, interruption and authorized tool handoff.
- Tests: `tests/multimodal/test_voice_session.py`, `tests/integration/test_voice_turns.py`.
- Acceptance: Real audio turn interrupted without stale playback or duplicate tool effects; latency, memory, packet bounds and account isolation measured.
- Security/integration risk: Cross-session audio and double effects during interruption; approvals must survive voice retries safely.
- Configuration: `ZENITH_VOICE_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 32. Document intelligence

Current: **PARTIAL**. Milestone: **M2**. Complexity: **L**. Prerequisites: 3, 20.

- Reuse: [agent/storage.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/storage.py); [scripts/import_dataset.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/scripts/import_dataset.py); [agent/core.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/core.py).
- Destination files: `agent/multimodal/documents.py`, `agent/document_index.py`.
- Work and expected behavior: Add isolated bounded document parsers, source spans/page/sheet coordinates, extraction and project-owned retrieval. Disable macros, formula execution and embedded actions.
- Tests: `tests/multimodal/test_documents.py`, `tests/test_document_index.py`.
- Acceptance: Real representative documents extract correctly; malicious/big inputs rejected; citations resolve to exact ingested spans; deletion/ownership preserved.
- Security/integration risk: ZIP/XML bombs, malicious PDF/Office content, source injection and tenant leakage.
- Configuration: `ZENITH_DOCUMENTS_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 33. Image generation

Current: **MISSING**. Milestone: **M6**. Complexity: **L**. Prerequisites: 29, 37.

- Reuse: [agent/web/zenith-banner.png](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/web/zenith-banner.png).
- Destination files: `agent/multimodal/images.py`, `agent/media_history.py`.
- Work and expected behavior: Add optional authorized generation/editing adapters, prompt refinement, provenance/history and local/cloud capability checks without replacing Zenith's text model.
- Tests: `tests/multimodal/test_images.py`.
- Acceptance: Actual authorized backend produces/edits an image; history records source/model/hash; unsupported models and missing credentials stay blocked.
- Security/integration risk: Provider terms, media rights, private references, credentials and large generated artifacts.
- Configuration: `ZENITH_IMAGE_GENERATION_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 34. Video intelligence

Current: **MISSING**. Milestone: **M7**. Complexity: **XL**. Prerequisites: 20, 29, 30, 32.

- Reuse: existing Store, authentication and execution boundaries.
- Destination files: `agent/multimodal/video.py`, `agent/video_index.py`.
- Work and expected behavior: Add sandboxed frame/audio extraction and sampled temporal summaries/search using verified vision/speech adapters; bound duration, frames and media storage.
- Tests: `tests/multimodal/test_video.py`.
- Acceptance: Known short videos produce correct timestamped frames/events; decoder isolated; resource limits enforced; answers cite actual frames/time ranges.
- Security/integration risk: Decoder vulnerabilities, misleading temporal summaries and resource exhaustion.
- Configuration: `ZENITH_VIDEO_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 35. Ollama integration

Current: **PARTIAL**. Milestone: **M2**. Complexity: **M**. Prerequisites: 5.

- Reuse: [agent/providers.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/providers.py); [agent/provider_adapters/local_adapter.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/provider_adapters/local_adapter.py); [agent/model_registry.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_registry.py).
- Destination files: `agent/provider_adapters/local_adapter.py`, `agent/providers.py`.
- Work and expected behavior: Add verified model-specific context/modality/tool metadata, availability monitoring and explicit lifecycle management without automatic model pulls/substitution.
- Tests: `tests/test_model_registry.py`, `tests/integration/test_ollama_native.py`.
- Acceptance: An actual configured Ollama model lists, answers and respects context/cancellation; unavailable/mismatched models fail clearly.
- Security/integration risk: Installed-model metadata does not establish compatibility; engine install/model download require operator selection.
- Configuration: `Existing AI_PROVIDER=ollama` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 36. NVIDIA/GPU optimization

Current: **PARTIAL**. Milestone: **M6**. Complexity: **XL**. Prerequisites: 8, 35, 37.

- Reuse: [agent/providers.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/providers.py); [agent/kv_cache.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/kv_cache.py); [agent/monitoring.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/monitoring.py); [scripts/inference_speed_benchmark.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/scripts/inference_speed_benchmark.py).
- Destination files: `agent/performance.py`, `agent/gpu_metrics.py`, `scripts/gpu_benchmark.py`.
- Work and expected behavior: Add GPU telemetry/profiling and benchmark compatible attention, quantization, batching/prefix caching and optional inference servers. Treat numerical changes as separately evaluated artifacts.
- Tests: `tests/test_gpu_metrics.py`, `tests/integration/test_gpu_inference.py`.
- Acceptance: Actual GPU records TTFT/TPS/VRAM/utilization and correctness against immutable CPU baseline; CPU fallback preserved; unsupported kernels/quantization remain blocked.
- Security/integration risk: VRAM exhaustion, numerical/adapter incompatibility and unsupported hardware; no universal speed claims.
- Configuration: `ZENITH_GPU_METRICS_ENABLED; new inference backends opt-in` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 37. Hybrid inference

Current: **EXISTING**. Milestone: **M2**. Complexity: **M**. Prerequisites: 5, 8.

- Reuse: [agent/orchestration.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/orchestration.py); [agent/task_router.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/task_router.py); [agent/provider_adapters/openai_adapter.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/provider_adapters/openai_adapter.py); [agent/provider_adapters/anthropic_adapter.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/provider_adapters/anthropic_adapter.py).
- Destination files: `agent/routing_metrics.py`, `agent/orchestration.py`.
- Work and expected behavior: Validate authorized live accounts and persist workload-aware metrics; extend modalities only after per-provider acceptance and privacy checks.
- Tests: `tests/test_orchestration.py`, `tests/integration/test_live_providers.py`.
- Acceptance: Live account tests run only with designated credentials; local-only stays offline; fallback respects model/tool/context/cost/privacy constraints.
- Security/integration risk: No configured API credentials here; unknown prices/access cannot be assumed; no provider-output distillation without rights.
- Configuration: `Existing AI_PROVIDER=orchestrated and explicit external permission` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 38. Training and fine-tuning

Current: **PARTIAL**. Milestone: **M6**. Complexity: **XL**. Prerequisites: 7, 8, 20.

- Reuse: [agent/continual.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/continual.py); [agent/checkpoints.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/checkpoints.py); [agent/curriculum.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/curriculum.py); [agent/deployment.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/deployment.py); [agent/export_checkpoint.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/export_checkpoint.py).
- Destination files: `agent/evolution/training.py`, `agent/continual.py`, `agent/expansion_eval.py`.
- Work and expected behavior: Add experiment tracking/trajectory curation and, where supported, separately validated QLoRA, optimizer resume and broader benchmarks. Keep original checkpoints immutable and failed gates intact.
- Tests: `tests/test_continuation.py`, `tests/test_deployment.py`, `tests/integration/test_training_lineage.py`.
- Acceptance: Start from exact verified trained parent; no random weights or parent writes; independent retention/security benchmarks pass before separately approved deployment.
- Security/integration risk: Forgetting, data leakage, licensing, optimizer/numerical incompatibility and unapproved deployment.
- Configuration: `Explicit training CLI plus ZENITH_EVOLUTION_TRAINING_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 39. MCP/plugin ecosystem

Current: **PARTIAL**. Milestone: **M4**. Complexity: **XL**. Prerequisites: 13, 20.

- Reuse: [agent/model_capabilities.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_capabilities.py); [agent/model_registry.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/model_registry.py); [integrations/inference_service/src/zenith_inference/chat_contract.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/integrations/inference_service/src/zenith_inference/chat_contract.py).
- Destination files: `integrations/mcp_service/pyproject.toml`, `integrations/mcp_service/src/zenith_mcp_service/client.py`, `agent/mcp_tools.py`, `agent/tool_registry.py`, `agent/tool_protocol.py`.
- Work and expected behavior: Add official-SDK MCP service/client, negotiated transports/resources/tools, schema validation, isolated stdio servers, approved remote origins and credential/capability mapping.
- Tests: `integrations/mcp_service/tests/test_protocol.py`, `tests/security/test_mcp_permissions.py`.
- Acceptance: Official conformance/real server round trips pass; tool/resource injection cannot grant authority; schema/transport/auth failures fail closed; no uncontrolled host stdio subprocess.
- Security/integration risk: Malicious descriptions/results, package execution, SSRF/OAuth leakage and self-granted tools.
- Configuration: `ZENITH_MCP_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.

## 40. Administration dashboard

Current: **PARTIAL**. Milestone: **M8**. Complexity: **L**. Prerequisites: 3, 5, 9, 14, 36, 38.

- Reuse: [agent/web/index.html](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/web/index.html); [agent/web/app.js](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/web/app.js); [agent/server.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/server.py); [agent/monitoring.py](https://github.com/n8storm/Zenith/blob/fcec8993b068cc72f2ca918a8ef5680dbc9b2255/agent/monitoring.py).
- Destination files: `agent/web/app.js`, `agent/web/index.html`, `agent/evolution/gateway.py`, `agent/monitoring.py`, `agent/role_policy.py`, `agent/agent_policies.py`, `agent/role_migrations.py`.
- Work and expected behavior: Extend the current interface with verified model/agent status, task progress, Evolution reviews, resource/usage metrics, training candidates and authorization history; absent sensors show unavailable.
- Tests: `tests/test_quality_admin.py`, `tests/integration/test_dashboard_permissions.py`.
- Acceptance: Real authenticated workflows exercise reviews/cancel/stop; cross-role APIs reject unauthorized actions; dashboards show measured data and explicit unavailable states.
- Security/integration risk: UI-only authorization is insufficient; display only capabilities actually enabled and verified.
- Configuration: `Per-subsystem flags; ZENITH_EVOLUTION_UI_ENABLED` (new flags are proposals, default off; they are not currently usable).
- Rollback: Disable this feature flag, drain/reconcile active effects, retain audit/receipts and previous release; restore reviewed database backup only if no newer writes would be lost. Never reset model weights or upstream state.
