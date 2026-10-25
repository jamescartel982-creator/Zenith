from report_helpers import *
from collections import Counter
G=PLAN['groups']; files=PLAN['files']; order=PLAN['group_order']
put('MASTER_FEATURE_PARITY_MATRIX.md',f'''# Master feature and coverage matrix

{COMMON}

The unabridged [CSV](MASTER_FEATURE_PARITY_MATRIX.csv) and [JSON](../evidence/master-feature-matrix.json) retain every indexed declaration, skill path, documentation surface and catalog reference. The [source mapping](SOURCE_TO_ZENITH_MAPPING.md) explains the 72 manually traced behavioral groups. There are **{len(ROWS)} coverage records, not {len(ROWS)} independent capabilities**: a channel can appear in its plugin, registration, documentation and tool records. No percentage of parity can validly be computed from these counts.

{table(['Record type','Rows'],SUMMARY['by_entry_type'].items())}

{table(['Zenith parity status','Rows'],SUMMARY['by_status'].items())}

`PARTIAL` means a Zenith equivalent covers part of the contract, sometimes only in unmerged PR #19. `NOT STARTED` means the proposed compatible implementation has not been accepted. `BLOCKED` includes external catalog packages whose source/license was not available in the audited checkout, and platform/service prerequisites. `IMPLEMENTED` requires production code; `VERIFIED` additionally requires the recorded supported-environment acceptance run. No new unified parity record is verified by this audit.

Each row includes reference project, pinned source, configuration/dependency reference, main equivalent, unmerged-pilot equivalent, missing behavior, integration strategy, destination files, security implications, acceptance files/behavior and status. Exact manifest schemas and environment **names** are retained in [manifest evidence](../evidence/plugin-manifests.json), not credential values. Import statements and dependency declarations are inventories, not a resolved dependency lock or proof of compatibility.

Applicability must be reviewed before implementation: documentation can describe the same feature, historical/restricted models, examples or unsupported platforms; fixture/vendor skills are coverage evidence rather than a request to install them. QA/test channels are test fixtures, not public messaging services. Reference-specific branding, release destinations, update URLs, account identities and telemetry are not applicable Zenith features. Legal access, source review, platform testing and behavior-level acceptance remain required for external plugins. Declared tools do not inherit execution permission.

Channel identities are enumerated independently (28 OpenClaw and 27 Hermes manifest declarations, plus 29 Hermes registration sites). They overlap and must not be summed as unique services. Protocol variants must retain their distinctions: personal-session WhatsApp and business/cloud WhatsApp, or callback and relay transports, cannot be treated as interchangeable. Each deployable variant needs its own actual service fixture and permission tests.
''')
rows=[]
for x in files:
 origin='main' if x['exists_on_main'] else ('PR19 only' if x['exists_in_pr19'] else ('PR18 only' if x['exists_in_pr18'] else 'new proposal'))
 rows.append([x['destination'],','.join(x['groups']),origin,x['expected_behavior'],', '.join(x['tests']),x['feature_flag'],x['rollback']])
put('FILE_BY_FILE_IMPLEMENTATION_PLAN.md',f'''# File-by-file implementation proposal

{COMMON}

**No destinations in this plan have been created or edited by the audit.** The [machine-readable plan](../evidence/file-by-file-plan.json) is authoritative for all {len(files)} unique proposed destinations, their dependencies, acceptance behavior, source feature IDs, blockers, branch existence and rollback instructions. {sum(x['destination'].startswith('tests/') for x in files)} entries are test destinations. Names and partitioning are review proposals; they are not an instruction to create empty modules.

Review base: {PLAN['review_base']}. Resolve PR18 planning/verification ownership and PR19 policy/task/migration ownership first. Keep public Agent.generate/stream and provider constructors working. Apply additive changes with default-off flags, not wholesale replacements. Preserve the checksum of shipped migration V1 and introduce versioned successors. Canonical channel/provider modules are separate review units, not an excuse for wrappers that lack real transport behavior.

Dependencies are group prerequisites in [the graph](DEPENDENCY_GRAPH.md). A test file implements its stated contract; test fixtures may simulate failures, but production transport acceptance needs a real supported backend. File rollback means disabling the relevant capability and retaining durable data; it does not mean deleting user history or reverting a live database blindly. Read [deployment/rollback](DEPLOYMENT_AND_ROLLBACK_PLAN.md) for sequencing.

{table(['Destination','Group','Already exists in','Expected behavior','Tests / verification','Default flag','Rollback'],rows)}
''')
mermaid=['graph TD']
for k in order:
 mermaid.append(f'  {k}["{k}: {G[k]["title"]}"]')
 for d in G[k]['deps']:mermaid.append(f'  {d} --> {k}')
put('DEPENDENCY_GRAPH.md',f'''# Dependency graph

{COMMON}

```mermaid
{chr(10).join(mermaid)}
```

{table(['Order','Group','Prerequisites','Acceptance gate'],[(i+1,k,', '.join(G[k]['deps']) or 'Expanded audit approval',G[k]['accept']) for i,k in enumerate(order)])}

The graph is acyclic. Logical ordering does not require a monolithic release. Shared policy, actor identities, schemas and isolation must pass before any effectful tool. Gateways and adapters consume one engine and store. Channel-specific work may proceed independently after shared contracts pass; it cannot bypass their gates. Finish each small pull request with tests, documentation, evidence and rollback, then review before enabling it. No calendar estimate or guaranteed parity date is justified by the present audit.
''')
put('SECURITY_THREAT_MODEL.md',f'''# Security threat model

{COMMON}

## Assets, actors and boundaries

Protect immutable model/adapter/tokenizer artifacts; user conversations and memory; credentials; host and remote systems; task grants; backups and audit integrity. Actors are authenticated users, owners, delegated workers, untrusted model outputs, websites, documents, remote tools, plugins, messaging peers and compromised service accounts. Boundaries are client→gateway, gateway→policy/store, model→tool proposal, policy→worker, worker→network/host, package→loader and tenant→memory. Compromised host/root is outside a process sandbox's protection; do not describe the HMAC log or Docker as proof against it.

Existing account Argon2id, owner MFA/session checks, revision-scoped grants and emergency stop remain authoritative. A gateway bearer establishes transport access, not owner privileges. The original random owner-code hashing and account password hashing serve different existing paths; do not replace either with a prompt secret. Never place credentials or MFA seeds in model context.

{table(['Threat','Required control / destination','Acceptance / residual limit'],[
('Forged owner or model self-authorization','agent/permissions.py and approvals.py derive actors from current server-side sessions, MFA and revision; object-level account/project ownership','Forged JSON role, expired session, revoked grant, cross-account task and argument mutation deny before any side effect; LLM cannot mint grants'),
('Prompt injection from web/skill/MCP output','tool_protocol.py labels untrusted content; policy computes permissions independently; approvals bind normalized arguments, target scope and revision','Injected instructions never enlarge scope; formatting/redaction is not the security boundary'),
('Code execution and escape','sandbox.py, sandbox_docker.py; disposable nonroot/rootless worker or stronger VM boundary, readonly root, no host home/socket/cookies, CPU/RAM/PID/output/wall quotas','Actual probes for symlink/junction traversal, mount/device/process abuse, forbidden file reads and timeout cleanup; not a universal escape-proof claim'),
('Missing sandbox or malicious package import','plugins/worker.py isolates processes; integrity hash and reviewed manifest, no host imports or automatic pip/npm hooks','Missing backend fails closed; hash mismatch/update reapproval; package metadata does not prove trust'),
('SSRF / covert egress','egress_policy.py network broker; deny by default; validate DNS/IP and redirects on every connection, IPv4/IPv6, loopback/private/cloud metadata; browser subresources, WebSocket and WebRTC coverage','Rebinding, redirect and proxy bypass probes; provider credentials only sent to pinned intended endpoint; OS/network isolation required, not URL validation alone'),
('Cross-tenant memory/history leak','ACL before retrieval/join/ranking; scoped IDs for summaries, caches, vectors and source attachments','Two-account collision and delete/expiry/export tests; old shared FTS remains explicitly shared until migrated'),
('Secrets in model/logs/results','secret_broker.py stores handles; inject at worker boundary, bounded structured logs, redaction/export policy and encrypted credential/backups','Canary secrets must not appear in provider prompts, tool output or audit metadata; pattern redaction cannot recognize every arbitrary secret'),
('Replayed or spoofed channel events','channels/router.py verifies platform signature, timestamp/replay ID, immutable owning identity; scoped outbox','Real callback replay/signature tests; revoke disconnected installations; service credentials required'),
('Duplicate external writes after crash','durable outbox plus intent ID and remote idempotency/reconciliation; task leases fenced','Crash before/after write then restart; ambiguous outcomes recorded for human review, never blindly replayed'),
('Admin/effectful schedule escalation','scoped service identity and expiring capability, revalidate on every tick/tool; emergency stop fences all workers','Expired owner, changed args, shutdown mid-flight; queued tasks cannot retain stale privilege'),
('Audit tampering / log failure','metadata HMAC chain and durable receipts; externally stored chain anchors where configured','Alter/delete/reorder tests and fail-closed on receipt failure; local key holder/root can forge local chain'),
('Abuse through delegation or remote/container tools','child capability is subset of parent; SSH pinned host/user; broker container operations without mounting Docker socket in workers','Cross-agent permission widening and target change denied; tools limited to owned/authorized targets'),
('Resource exhaustion / cancellation leaks','quotas and admission control; bounded parallelism, per-model queue, process-group cancellation, lease cleanup','Concurrency/flood/cancel/disconnect/restart tests; no unbounded token/tool loops'),
('Training or skill poisoning','consented provenance, immutable candidate versions, scan plus isolated tests, frozen heldout, explicit review and rollback','Failed examples not treated as successes; no production code changes or live weight updates; original checkpoint hash unchanged')])}

## Approval and operation policy

Read-only search and low-impact tools may be allowed by a scoped policy. Writes, external sends, repository publication, remote execution, credential handling, security scans and destructive changes require the configured explicit approval; an approval for one action is not approval for arbitrary future actions. Cybersecurity tools require an authenticated authorized actor, explicit target/expiry, safe limits and a bounded supported tool. No malware deployment, credential theft or retaliation feature is in this design.

Default all new effectful tools off. External access stays loopback/closed until authentication, origin/CSRF, rate-limit, reverse-proxy/TLS and tenant tests pass. Prompt injection and sandbox tests are finite tests, not certification. Root compromise, unknown kernel/runtime vulnerabilities, malicious legitimate owner actions and external-service outages remain residual risks. Release notes must state tested environments and open findings.

Security acceptance owners: G01 policy/migrations, G02 isolation/egress, G04 lifecycle, G05 retrieval isolation, G07 supply chain/MCP, G08 delegation, G09 channel identity, G10 unattended execution, G11 remote/browser actions, G15 release audit. Exact test paths are in the file plan.
''')
put('AUTOMATED_TEST_PLAN.md',f'''# Automated acceptance and regression plan

{COMMON}

## Evidence levels

A parser/import test verifies only that narrow property. Unit tests may use deterministic fakes for fault injection; integration tests must exercise real SQLite, process/transport boundaries and actual configured backends. End-to-end parity needs frozen reference-equivalent workloads, the unchanged selected Zenith checkpoint, recorded scopes and independent outcome checks. Passing unit tests alone never upgrades a feature to VERIFIED. Every run records repository SHA, configuration and fixture hashes, model/tokenizer/adapter hashes, platform, dependency lock, command, seed, raw timings, results and exclusions. Credentials and private conversations are excluded from public artifacts.

## Required acceptance by subsystem

{table(['Group','Required executable gate','Primary test destinations'],[(k,G[k]['accept'],', '.join(G[k]['tests'])) for k in order])}

Additional per-integration assertions are specified in [the full matrix](MASTER_FEATURE_PARITY_MATRIX.csv) and [file plan](FILE_BY_FILE_IMPLEMENTATION_PLAN.md). Each channel tests real inbound/outbound protocol, signature/replay, identity mapping, threading, edit/delete/reactions/media where supported, payload limits, retry/reconciliation and revocation. Each provider tests account-visible discovery, exact IDs, modalities, tool schema, streaming/cancellation and error/failover attribution. Unconfigured external services remain BLOCKED; a fake adapter is not a production pass.

## Workloads and gates

1. Baseline/regression: fresh main suite plus unchanged native checkpoint inference. Candidate must preserve existing public APIs, data, login and local installation. Compare on identical model and hardware, not stronger replacement weights.
2. Deterministic agent tasks: owned temporary Git repo (inspect→patch→test→verify), SQLite query→chart artifact, scoped retrieval→answer/source check and failure→correction. Use independent file/db assertions and real bounded tools; report model selection, budget and complete task outcomes.
3. Memory: synthetic two-account/project corpora, duplicate/expired/deleted facts, relevant/irrelevant passages, summaries and restart; recall@k/MRR plus zero cross-account returned rows. Do not train on heldout queries.
4. Skills/learning: successful/failed/rescued trajectories, inactive candidate generation, isolated tests, poisoned skill rejection, human review/version activation, regression and rollback; compare heldout task success and unnecessary tool/token cost.
5. Security: all denial cases in the threat model, prompt-injection fixture corpus, approval mutation/replay, outbound canary endpoints, forbidden host-file probes, audit failure, scope revocation under load and emergency shutdown. Require zero prohibited side effects in these fixtures; do not claim universal safety.
6. Persistence/recovery: kill worker at each task transition, SQLite busy/disk-full/failure injection, WAL-consistent backup, lease fencing, unknown external writes, duplicate callback/outbox replay and mixed old/new schema writer behavior.
7. Multi-agent: disjoint workspaces, shared bounded information, conflicting patches, scoped children, supervisor cancellation and bounded parallelism; shared local model uses serialization until tested otherwise.
8. Media/clients: real licensed fixtures with OCR accuracy, transcription WER, actual audio playback/file validity, image/video pipeline source attribution and missing-dependency behavior; OS-specific UI permission tests on actual supported systems. Text-only installation must still work.
9. Knowledge/reasoning/coding: freeze appropriately licensed GSM8K, HumanEval+ and selected SWE-bench fixtures with contamination/provenance notes; sandbox executable code tests. These benchmarks are planned, not run. A small selected model may fail; report failure rather than silently swapping it.
10. Performance: monotonic TTFT/full latency, tokens/s, input/output/tool tokens, RSS/VRAM/GPU, errors, provider spend, concurrency and successful-task cost. Warm/cold runs and output lengths separated; no speedup claim from the current two-probe sample.

## Promotion and publication

Pin fixture revisions and hashes before tuning. Separate train/replay/development/test partitions and preserve their provenance. Candidate skill/code/adapter evaluation has separate quality and authorization gates. Failed gates remain failed; exceptions, if allowed, must be explicitly recorded and cannot relabel a score. No automatic adapter promotion. Independently review code, migrations, licenses, security and model-quality evidence; publication is separate from running local tests.
''')
put('BENCHMARK_BASELINE.md',f'''# Measured baseline and proposed benchmark protocol

{COMMON}

## Measured in this audit

Zenith fresh main `e6963d9` ran `python -m unittest discover -s tests -v` using the existing `/workspace/Zenith/.venv/bin/python`, isolated `ZENITH_HOME`, CPU-only workspace. **243 tests ran: 242 passed, 1 skipped, 33.364 seconds.** See [raw log](../evidence/zenith-main-tests.log). A skipped test is not a pass.

Native offline `python -m scripts.smoke_orchestration --bundle research_checkpoints/recovery-v1` used the current cached selected base and adapter, without activating or modifying it. [Raw output](../evidence/zenith-main-native-baseline.json): cold load **6.503 seconds**; arithmetic direct **875.938 ms** / routed **655.735 ms**, both answer 4; geography direct **887.078 ms** / routed **712.474 ms**, both answer Paris. Weight/profile unchanged flags passed. These are two correctness probes, not general intelligence, agent-completion, or throughput benchmarks. Order/warm-cache effects prevent a speedup conclusion.

## Earlier unchanged-commit pilot evidence, not rerun here

Draft PR #19 `44d55d2` previously ran 277 tests: **276 passed, 1 skipped, 40.248 seconds**. Its Windows/Linux/container checks are linked in the delivery index. Prior native direct/queued 3-pair smoke medians were **6423.591 ms / 9855.643 ms**, matching outputs and 220 output tokens each. The queue was slower on that sample; no performance improvement is claimed. This pilot handles explicit supervised plans and fixed diagnostics, not the proposed autonomous unified platform. PR18 and PR19 are unmerged.

## Not measured

OpenClaw/Hermes runtime tests, reference-equivalent task success, shell/browser isolation, new skill learning, channel delivery, multi-agent coordination, semantic retrieval relevance, prompt-injection resistance, sandbox escape resistance, concurrency, TTFT, GPU/VRAM, complete token cost and new multimodal/UI acceptance have not been run. No scores or zero-error rates are assigned to them.

## Frozen comparison protocol (proposal)

Before implementation, freeze workload IDs, fixture content/config hashes, success assertions and budgets; preserve them for baseline/reference/candidate. Run OpenClaw and Hermes in supported independent environments at the pinned commits with the **same** Zenith endpoint/model identity where technically compatible. An incompatible tool dialect is a reported blocker, not a reason to use Hermes weights. Match tool permissions, datasets, resource caps, retries, network targets and warmup. Separate reference defaults from normalized runs, because default provider/model differences confound comparisons.

For each cell record environment, dependency versions, model source, latency distribution (median/p95 and raw samples), complete/partial/failed/blocked counts with denominator, unauthorized attempts/effects, retrieval ranking, successful coordination, restart survival, token consumption and estimated versus billed cost. Use enough independent repeated tasks to report uncertainty; do not infer p95 from a two/three-pair smoke. Independent validators check the result, not the model's self-rating. Security suites report attempted cases, observed effects and tested boundaries, never a universal resistance percentage.

Store immutable experiment manifests under `benchmarks/unified/`, results under an opt-in non-private output directory and aggregate reports with raw reproducible evidence. Baseline model-only and disabled-platform overhead runs remain separate from full task-completion workloads. No benchmark may mutate the original checkpoint, production profile or user data.
''')
put('PRIORITIZED_ENGINEERING_MILESTONES.md',f'''# Reviewable engineering milestones

{COMMON}

Each group below is a milestone with one or more small PRs; large integration families must be split per adapter/transport. Do not generate every planned file in a single commit. All capabilities remain disabled until their actual acceptance gate passes on a named environment. Preserve earlier branches and review PR18/19 before choosing a base.

{table(['Milestone','Scope','Depends on','Exit / review evidence'],[(k,G[k]['title'],', '.join(G[k]['deps']) or 'Expanded audit approval',G[k]['accept']) for k in order])}

First implementation review: reconcile existing PR ownership without merging silently; extend policy/identity/migrations and add isolated execution; then the first typed tool loop must complete a bounded real task with the current Zenith checkpoint. If its tool-use quality is insufficient, report the measured limitation and separately propose controlled compatible training. Do not substitute a stronger model while calling the result Zenith-native parity.

Service-credential work, mobile signing, desktop OS access, hardware-dependent media, external catalog package provenance and independent reference runtimes form explicit blocker queues. Each blocked matrix row needs a maintainer decision: supply prerequisites, approve an alternative, or document a scoped exclusion. No feature may disappear from the matrix merely because it is difficult. A deadline cannot be estimated credibly before these prerequisites and early model/task measurements are resolved.

Every PR description must state the concrete behavior, evidence, security boundary, source/license attribution, exact default-off activation, migration/rollback and known limitations. `IMPLEMENTED` after code review is distinct from `VERIFIED` after integration acceptance. Overall parity remains unclaimed until all applicable contracts pass or exclusions are explicitly approved.
''')
put('DEPLOYMENT_AND_ROLLBACK_PLAN.md',f'''# Deployment, migrations and rollback proposal

{COMMON}

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
''')
put('LICENSE_AND_COMPATIBILITY.md',f'''# License, dependency and platform compatibility

{COMMON}

OpenClaw root license is MIT (OpenClaw Foundation, 2026); Hermes root license is MIT (Nous Research, 2025). Zenith is Apache-2.0. MIT code can generally be incorporated while preserving the copyright/permission notices; this audit is not legal clearance for every transitive asset or plugin. [License inventory](../evidence/license-inventory.json) records source license/notice files; [dependency declarations](../evidence/dependency-declarations.json) records declared roots/workspaces, not a resolved transitive SBOM. Public root license texts are included in the evidence folder. No upstream source code, assets or model weights were copied into Zenith by this audit.

Before copying or adapting any implementation, pin the exact files/commit, retain required MIT notices and applicable third-party notices, review bundled fonts/media/vendor libraries, record provenance in Zenith NOTICE/THIRD_PARTY_NOTICES, and review resolved optional dependencies, native binaries, model and dataset terms. Preserve attribution even if symbols are renamed. Reimplementing a compatible protocol does not grant access to a proprietary service or authorize reuse of its branding, credentials, outputs or training data. Catalog-only packages (827 references) remain blocked until their own source and licenses are reviewed.

{table(['Component','Pinned runtime / dependency constraint','Compatibility decision'],[
('Zenith main','Current Python local install; preserved CPU Transformers/PEFT adapter path','Keep core and text-only path; optional capabilities must not force incompatible dependency upgrades'),
('OpenClaw','Node >=24.22.1 <25 or >=26.12.1; pnpm12.15.0; SQLite/native and platform packages','Current Node24.19.0 is unsupported; source audit only, no upstream runtime verified'),
('Hermes root/PM','Bridge requires-python >=3.11,<3.15; managed PM >=3.14,<3.15; .python-version 3.14; Node>=26','Python3.12 AST parsing is not runtime support. Independent managed environment needed for reference execution'),
('Hermes dependency overlap','Most root dependency markers >=3.14; cryptography50.0.2 versus Zenith>=44,<48','Do not merge requirements wholesale; implement native contracts or isolate reviewed workers'),
('Hermes desktop','Electron and Node>=26; platform packaging/signing policies differ','No implicit Linux desktop release support from build scripts; actual target OS acceptance needed'),
('Optional services/models','Account-visible APIs, credentials, API terms, retirement and quota policies','Unavailable/restricted models remain unavailable; discover exact authorized IDs, do not fabricate family availability'),
('Third-party packages/catalog','Remote referenced source not necessarily vendored or covered by root MIT','BLOCKED pending provenance, lock resolution, security and license review'),
('GPU/mobile/browser','Hardware, OS permissions, sandbox and native package constraints','Keep optional; report unsupported or untested combinations explicitly')])}

Hermes supported-platform policy includes macOS arm64 desktop, Windows10/11 CLI and Windows11 22H2+ MSIX, Linux/WSL2 CLI and Docker; Nix/Android Termux aarch64 are best-effort. Upstream policy is not evidence those platforms work in Zenith. Current host has no demonstrated GPU and lacks supported reference Node versions. No automatic dependency installation or upstream setup script was executed.
''')
put('FEATURE_PARITY_REPORT.md',f'''# Feature parity report

{COMMON}

**Full parity is not achieved or claimed. This delivery is an audit and review proposal.** Zenith main has its existing model/chat, provider orchestration, owner controls, memory, training/evaluation and deployment infrastructure; PR19 adds a default-off supervised task pilot, not an autonomous replacement agent. Neither open PR is treated as merged. The source audit does not itself implement any of the new unified features.

{table(['Status','Coverage records'],SUMMARY['by_status'].items())}

These are overlapping coverage records, not independent-feature completion percentages. The complete matrix retains 72 traced behavioral groups, 292 plugin declarations, 55 channel manifest identities, 29 platform registration sites, 90 model-provider identities, 51 production Python tool registration calls, 55 toolset members, 339 skill paths, 1855 documentation surfaces, 827 external catalog references and 7 execution backend records. Some rows are fixtures, vendor packages, alternative transports, historical docs or repeated descriptions and need explicit applicability decisions. No external catalog plugin is declared implemented from a URL alone.

Measured baseline: fresh-main 242 passed/1 skipped; two native inference probes produced matching direct/routed answers. Those results protect existing behavior, not feature parity. Upstream runtime tests and unified acceptance are not run. The selected local adapter's previously failed numerical quality/retention gates remain failed; its existing owner exception is not a new success or promotion.

## Open blockers and decisions

- Expanded audit approval is required before Zenith implementation under the latest user instruction.
- PR18/19 remain open and overlapping; select/reconcile a reviewed base, preserving both branches and all model/data artifacts.
- Reference runtimes need supported Node/Python environments, dependency installation and their own bounded execution policies before equivalent live comparisons.
- Actual model tool-use and planning capability must be measured with unchanged selected Zenith; an integration cannot guarantee a small model's task quality.
- Messaging/provider services need legitimate account access and per-transport testing; API keys do not grant universal model access.
- External catalog packages need source/license review; platform apps require build/signing/devices and OS permissions.
- Sandbox/browser/remote/GPU/media/concurrency/learning acceptance remains unmeasured. These are missing engineering work, not documentation-complete features.
- A source inventory can be broad without proving every dynamic branch. Regex/AST metadata, manifests and doc headings are coverage aids; runtime equivalence and security require the planned executable tests. Later reference commits require a new delta audit.

Each implementation PR must move only its tested rows forward and retain blocked/unimplemented rows. Final acceptance requires all applicable contracts verified or explicit approved exclusions, with real environment and test evidence. No claim that Zenith became Hermes, OpenClaw, a proprietary frontier model or a newly trained foundation model is warranted.
''')
print('delivery reports written:',len(list(R.glob('*.md'))),'markdown files')
