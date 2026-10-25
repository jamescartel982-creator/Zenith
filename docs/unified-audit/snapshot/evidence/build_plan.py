from pathlib import Path
import collections,json,re
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';R=ROOT/'reports'
rows=json.loads((E/'master-feature-matrix.json').read_text());groups=json.loads((E/'group-dependencies.json').read_text())
main=ROOT/'zenith-main';pilot=Path('/workspace/zenith-platform')
plan={}
def add(path,group,behavior,features=(),test=None,blockers=()):
 if path in plan:
  plan[path]['feature_ids'].update(features);plan[path]['groups'].add(group);return
 filename=Path(path).stem
 tests=test or groups[group]['tests']
 plan[path]={'destination':path,'groups':{group},'dependencies':set(groups[group]['deps']),
  'exists_on_main':(main/path).exists(),'exists_in_pr19':(pilot/path).exists(),'exists_in_pr18':(Path('/workspace/Zenith')/path).exists(),
  'change_after_pr19':'extend' if (pilot/path).exists() else 'new',
  'expected_behavior':behavior,'tests':list(tests),
  'acceptance':groups[group]['accept'],'feature_ids':set(features),
  'feature_flag':'unified_'+group.lower()+'_enabled=false',
  'rollback':'Deny new admissions, revoke affected grants, cancel/drain owned workers, disable this feature flag; keep additive tables/audit history and old APIs. Never overwrite models or restore over newer user data.',
  'blockers':list(blockers)}
for group,g in groups.items():
 for path in g['dest']:
  add(path,group,g['title']+': implement only this file-owned contract, preserving existing owner/public interfaces. '+g['accept'],[r['id'] for r in rows if r['group']==group and r['entry_type']=='core_behavior'])
# Add missing concrete owners for broad group responsibilities.
extra=[
('agent/platform_config.py','G01','Add default-off validated flags/quotas; reject unsupported combinations. Keep existing base-install defaults.'),
('agent/config.py','G01','Append backward-compatible settings; preserve selected provider/checkpoint/tokenizer and existing env precedence.'),
('.env.example','G01','Examples use credential variable names only, no embedded values; each new capability defaults off.'),
('agent/platform_repository.py','G01','Reuse Store connection; additive versioned migrations with old writer tests, consistent backup, scoped queries and bounded canonical data.'),
('agent/skill_access.py','G06','Preserve existing protected prompt-profile behavior; candidate activation never grants tool execution.'),
('agent/skills.py','G06','Add immutable reviewed candidate references beside existing profiles; label prompt skills, workflow recipes and executable packages separately.'),
('agent/research_agent.py','G13','Multi-query plan/retrieve/synthesize with actual bounded sources, scoped knowledge and unverified-claim reporting.'),
('agent/source_verifier.py','G13','Verify retrieved source identifiers, support and contradictions; never invent a fetched page or treat every example URL as a citation.'),
('agent/citation_manager.py','G13','Persist real source/version/excerpt citations per task/account and purge derived copies according to retention/deletion policy.'),
('agent/context_snapshot.py','G05','Version immutable system/tool prefix snapshots per session; fresh account-scoped memory in bounded data context; invalidate caches explicitly.'),
('agent/personal.py','G05','Adapter for existing notes, ownership, expiration/deletion; preserve legacy tables and user-controlled saved memories.'),
('agent/summaries.py','G05','Keep current manual summaries; add checkpoint-aware compression adapter without reclassifying summaries as facts or instructions.'),
('agent/core.py','G03','Opt-in autonomous dispatch/privacy/context hooks around current Agent and lock; old answer/stream signatures continue.'),
('agent/provider_adapters/openai_adapter.py','G13','Explicit optional structured tool-turn transport with real account access/usage/schema validation; old text contract remains.'),
('agent/provider_adapters/anthropic_adapter.py','G13','Explicit authorized content/tool-use transport; no proprietary activation/hidden-reasoning claims.'),
('agent/execution.py','G01','Preserve existing seven fixed capabilities and MFA/emergency/grant checks; share live authorization with every new broker.'),
('agent/redaction.py','G01','Redact before prompt/provider/log/tool egress using configured secret handles and synthetic-canary regression tests; no heuristic as sole gate.'),
('agent/process_manager.py','G02','Broker-owned process lifecycle, output/read/wait/kill, short-lived capability context, resource budgets and restart cleanup.'),
('agent/credential_vault.py','G11','Origin/target-bound opaque handles and explicit human fill/save decisions; never return plaintext credentials to model or worker logs.'),
('agent/compat/openclaw_rpc.py','G04','Optional version-negotiated OpenClaw-compatible subset mapped into the same Zenith task engine; no shared-secret operator promotion.'),
('agent/compat/hermes_rpc.py','G04','Optional tested Hermes UI/ACP protocol adapters into the same engine, not an imported AIAgent or second model service.'),
('agent/model_lineage.py','G06','Thin adapter to current checkpoints/continuation/export owners; verify immutable parent hashes/tokenizer and record all failed gates.'),
('agent/skill_review.py','G06','Human review binds candidate hash/version/required scopes; activation/deactivation/rollback cannot widen grants.'),
('agent/evaluation/skill-learning-v1.json','G06','Frozen authorized success/failure/held-out skill-learning fixtures with licenses, leakage checks and retention scoring.'),
('agent/hooks.py','G10','Untrusted hook declarations use typed event data and the sandbox/policy broker; no arbitrary in-process shell callbacks.'),
('config/unified-policy.example.json','G01','Document account roles, scoped targets, quotas, approvals and secret references; owner execution remains explicitly disabled.'),
('config/sandbox-policy.example.json','G02','Pinned approved images, no-network baseline, mounts/CPU/memory/PID/output/time budgets and fail-closed unsupported platforms.'),
('deploy/systemd/zenith.service','G15','Least-privilege Linux service with private data/runtime directories and controlled environment; no model/admin secrets embedded.'),
('deploy/compose.gpu.yaml','G15','Optional NVIDIA inference service separated from orchestration with explicit device/driver checks; CPU base compose unchanged.'),
('deploy/remote-linux.md','G15','Owned host deployment, TLS/proxy/auth/egress/backups/rollback and compute readiness; never assume GPU.'),
('docs/unified-platform/architecture.md','G15','Document actually implemented contracts, schema versions, source provenance, unavailable flags and model preservation.'),
('docs/unified-platform/operations.md','G15','Document installation, accounts/grants, secrets, service/device setup, migrations, cancellation and safe rollback.'),
('docs/unified-platform/parity-results.json','G15','Machine-readable fixture/config/source hashes and actual pass/fail/blocked outcomes per capability; no proposal marked verified.'),
('README.md','G15','Professional concise capabilities and normal install flow; preserve logo and explicitly distinguish native inference from optional integrations.'),
]
for path,group,behavior in extra:add(path,group,behavior)
# One canonical channel module can serve source-specific modes; retain each reference row's acceptance facets.
alias={'msteams':'teams','googlechat':'google_chat','nextcloud-talk':'nextcloud_talk','synology-chat':'synology_chat'}
for row in rows:
 if row['entry_type'] not in {'channel_integration','platform_registration','model_provider_identity'}:continue
 name=str(row['feature_name'])
 if row['entry_type'] in {'channel_integration','platform_registration'}:
  name=alias.get(name,name);slug=re.sub('[^a-z0-9_]','_',name.lower())
  path=f'agent/channels/{slug}.py';group='G09';tests=[f'tests/channels/test_{slug}.py','tests/e2e/test_unified_channel_accounts.py']
  behavior=f'{name}: native Zenith adapter, explicit identity binding, signed/replay-bounded ingress, approved outbox, all applicable text/media/thread/edit/reaction/chunking/config facets from source profile. No duplicate Hermes/OpenClaw agent daemon.'
  blocks=['Owned account/device/credentials required for actual source-equivalent E2E.']
 else:
  slug=re.sub('[^a-z0-9_]','_',name.lower());path=f'agent/provider_adapters/{slug}_adapter.py';group='G13';tests=[f'tests/providers/test_{slug}.py','tests/integration/test_unified_providers.py']
  behavior=f'{name}: optional provider transport integrated with current registry; exact legitimate account-visible model/capability discovery, privacy/usage/error controls, structured calls only where tested. Zenith native stays default.'
  blocks=['Provider account/terms/capability access and selected dependency lock/license review required.']
 add(path,group,behavior,[row['id']],tests,blocks)
# Proposed test destinations are explicit changes too, not declarations of passing tests.
test_map=collections.defaultdict(list)
for path,item in list(plan.items()):
 for test in item['tests']:test_map[test].append(path)
for test,owned in sorted(test_map.items()):
 g=next(iter(plan[owned[0]]['groups']))
 add(test,g,'Behavioral tests for '+', '.join(owned)+'. Compose real owned dependencies and preserve independent fixtures; unavailable backends are blocked, not mocked production success.',test=[test])
for marker in ('agent/plugins/__init__.py','agent/channels/__init__.py','agent/multimodal/__init__.py','agent/compat/__init__.py'):
 add(marker,'G07','Inert package marker only; no eager registry imports, environment installs or execution.',test=['tests/test_unified_imports.py'])
add('tests/test_unified_imports.py','G07','Real imports in an isolated temporary Zenith home must not install dependencies, connect to services, change profile state or execute plugins.',test=['tests/test_unified_imports.py'])
# Merge group dependency requirements for shared files; require enabling prerequisites, not a second ownership stack.
OWNERS={
 'agent/tool_protocol.py':'Versioned immutable ModelTurn/ToolCall/ToolResult schema; bounded arguments, finish reasons, actual usage and schema-dialect negotiation. Never parse free-form chat as authority.',
 'agent/tool_registry.py':'Exact tool/version/schema/effect/target/dependency registry; runtime availability distinct from grants, live per-effect authorization and output bounds.',
 'agent/autonomy.py':'Bounded plan-act-observe-verify loop over the current native provider, durable task store and broker; bounded repair and abstention when local tool competence fails.',
 'agent/planning.py':'Extend/reconcile PR18 if adopted: structured goals, step dependencies, checks and shared inference/tool budgets; concise plan data, not proprietary hidden reasoning.',
 'agent/verification.py':'Reconcile PR18 numeric verification; independent source/math/code/goal checks and uncertainty, with code only in approved isolated worker.',
 'agent/runtime.py':'Extend supervised PR19 runtime with opt-in autonomous modes while preserving explicit plans, local-default selection, lock ownership, heartbeats, cancellation and conservative reconciliation.',
 'agent/task_store.py':'Fenced durable task/step/effect leases, explicit checkpoints, versioned transitions and idempotency receipts; never silently retry an uncertain accepted write.',
 'agent/event_bus.py':'Transactional scoped events with cursor replay, bounded live subscribers and backpressure; retain approval and terminal outcomes.',
 'agent/session_manager.py':'Account/project/session ownership, session snapshots and lifecycle; preserve current conversations and explicitly bind worker/profile context.',
 'agent/websocket_gateway.py':'Zenith versioned frame/auth negotiation, bounded subscriptions, cancellation and reconnect/replay; compatibility adapters separately versioned/tested.',
 'agent/semantic_memory.py':'Optional pinned licensed embeddings as derived scoped index; lexical fallback first, actual relevance/CPU cost gate, deletion and expiry purge derived copies.',
 'agent/episodic_memory.py':'Consented account/project task episodes with provenance, confidence, TTL and deletion; do not turn inferences into authoritative user facts.',
 'agent/trajectory_store.py':'Consent- and license-tagged successes/failures, step/tool/usage/outcome records, secret redaction and immutable held-out exclusion; no automatic provider-output training.',
 'agent/skill_learning.py':'Generate immutable typed candidate skills/workflows from consented traces and native model proposals; every output remains untrusted and inactive.',
 'agent/skill_evaluation.py':'Run candidate workflow in owned isolated fixtures; compare goal success, authorization, tokens/cost/latency and regression/retention against frozen baseline.',
 'agent/skill_versions.py':'Content hashes, source/license lineage, parent version, review/evaluation records, explicit activation and reversible rollback.',
 'agent/workflow_discovery.py':'Mine reusable action/data dependencies from successful and failed traces; replace secrets with handles and require fresh live permissions for every replay.',
 'agent/multi_agent.py':'Supervisor/child identity lifecycle, strict subset delegation, shared quotas, steering/cancel and audited handoffs; federation is separate.',
 'agent/specialists.py':'Configure coding/research/data/infra/security/planning/memory/testing/docs/automation postures with explicit tool subsets, not self-granted privileges.',
 'agent/task_graph.py':'Durable dependency/review/block/heartbeat/attachment graph with child leases, idempotent completion and failed/reconciled states.',
 'agent/workspace_manager.py':'Isolated Git worktrees and filesystem roots, change/test logs, resumable task snapshots and scoped cleanup; never silently commit or push.',
 'agent/scheduler.py':'UTC and fully tested cron/timezone/DST schedules, overlap/misfire rules and lease-fenced dispatch under explicit expiring service grants.',
 'agent/outbox.py':'Transactional delivery intent/receipt and provider idempotency where supported; accepted-timeout uncertainty enters reconciliation.',
 'agent/remote_execution.py':'Authenticated owned SSH/cloud execution through brokers, pinned host identity, narrow user/mount/network scopes, quotas and resource cleanup.',
 'agent/telemetry.py':'Bounded account/task/span/token/latency/error/resource metadata; optional redacted exporters off by default, unknown measurements remain unknown.',
}
for path,behavior in OWNERS.items():
 if path in plan:plan[path]['expected_behavior']=behavior
for p,item in plan.items():
 item['dependencies']=sorted(set(d for g in item['groups'] for d in groups[g]['deps'])-item['groups'])
 item['groups']=sorted(item['groups']);item['feature_ids']=sorted(item['feature_ids'])
# Check the group graph for cycles.
seen=set();order=[]
while len(seen)<len(groups):
 ready=[g for g in groups if g not in seen and set(groups[g]['deps'])<=seen]
 assert ready,'Group cycle'
 seen.update(ready);order.extend(ready)
value={'status':'proposal_only; no Zenith code changes permitted until this audit is approved','review_base':'main e6963d9; pilot PR19 44d55d2 and reasoning PR18 ac989d8 are unmerged. Reconcile overlapping owners after audit approval; preserve both branches.','group_order':order,'groups':groups,'files':list(plan.values())}
(E/'file-by-file-plan.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'proposed_file_changes':len(plan),'proposed_source_config_files':len(plan)-len(test_map),'explicit_test_files':len(test_map),'groups':len(groups),'acyclic':True}))
