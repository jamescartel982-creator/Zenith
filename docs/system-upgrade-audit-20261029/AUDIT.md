# Current repository audit

## Scope and evidence standard

GitHub `main` and the clean local checkout both resolved to
`fcec8993b068cc72f2ca918a8ef5680dbc9b2255`, tree
`db9408a8f50826531b71fc97af825138605ee928`. Git tracks 715 files. The release
manifest verified its 714 non-self entries. All tracked bytes were inventoried;
251 Python modules parsed without syntax errors. Definitions, imports, routes,
JSON parse status, documentation headings and SHA-256 are retained in
[source-inventory.json](source-inventory.json). [FILE_INVENTORY.md](FILE_INVENTORY.md)
maps each Python module to its definitions and source lines.

Coverage is a complete structural inventory plus targeted semantic source review
of model/provider, reasoning, memory, runtime, training, security, bridge, UI and
deployment owners. It is not a formal verification, exhaustive penetration test
or claim that every line of historical documentation is current. Binary images
and frozen model parts were hashed, not treated as executable source.

Evidence levels used throughout:

- **Source verified:** behavior implemented in the pinned source.
- **Fresh executable evidence:** tests or real inference run during this audit.
- **Historical executable evidence:** dated reports/CI from an earlier commit.
- **Proposed:** destination and acceptance criteria only; not installed code.
- **Blocked/unverified:** missing credentials, hardware, OS support, environment
  capacity or acceptance evidence. Absence is not filled with a simulated result.

## Architecture and identity

Entrypoints are `agent.commands:main` / `agent.server:main`; installers and
activation scripts support the existing Windows/Linux/macOS paths. `agent.core.Agent`
coordinates request budgets, selected skill, account memories, shared retrieval,
streaming generation, review metadata and storage. The existing provider factory
supports Hugging Face, Ollama, a loopback compatible endpoint, ensemble,
orchestration, reasoning and a separate legacy Tiny experiment. The selected
trained Zenith lineage is not the optional Tiny model.

Fresh strict loading used `agent.checkpoints.load_existing`: exact base loading
keys, saved-tokenizer equality, finite learned adapter tensors and nonzero LoRA B
values were checked. The selected model was **not** reinitialized or retrained.

| Property | Verified value |
| --- | --- |
| Base/model type | Qwen/Qwen2.5-0.5B-Instruct / Qwen2ForCausalLM / qwen2 |
| Base revision | 7ae557604adf67be50417f59c2c2f167def9a775 |
| Parameters | 494,032,768 base; 4,399,104 LoRA; 498,431,872 total |
| Layers / hidden size | 24 / 896 |
| Attention / KV heads | 14 / 2 |
| Context | 32,768 architectural; 2,048 selected input budget in this baseline |
| Tokenizer / embeddings | 151,665 tokenizer entries / 151,936 embedding entries |
| Format | Existing PEFT LoRA safetensors + pinned base safetensors |
| Torch / Transformers / PEFT | 2.14.1+cpu / 5.10.4 / 0.18.1 |
| Strict load | 15.876 seconds, includes integrity work; not pure cold disk-load throughput |

Identity and artifact hashes:

- Preserved identity: `182559bbb77dad2ac9f53be2252ef0fa8a3698851d8d47708d5264701170e13b`.
- Base safetensors: `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
- Adapter safetensors: `7e0701900b40109ee81b3dc097985cda360409006c8b717bda51830f3b6ed85d`.
- Tokenizer file: `9c5ae00e602b8860cbd784ba82a8aa14e8feecec692e7076590d014d7b7fdafa`.
- Semantic tokenizer signature: `221ea68122dfcfb2772276b69e62fc97ea9b13785ee069b118ee36498b19a418`.
- Loaded parameter fingerprint: `9abde1fc20e926e8e8ba62660bf14155c3cb6c0e67bb794164a1a758278f6b60`.

File and semantic tokenizer hashes are different measurements. Their difference
does not indicate tokenizer modification. The baseline verifies both original
artifacts and unchanged loaded parameters before/after inference.

Training infrastructure exists: licensed/grouped train/validation/test curation,
reviewed feedback export, LoRA SFT/CPT/DPO continuation, historical replay,
checkpoint inventory/lineage, retention evaluation, merge/export checks and manual
activation/rollback. Historical six-stage training evidence records 1,064 optimizer
steps and 69,228 input tokens. It is a small CPU experiment, not comprehensive
domain training. The current adapter's historical experimental quality decisions
and failed retention/promotion comparisons remain recorded; this audit changes
none of them. QLoRA, optimizer-state resume and large distributed training are not
verified implementations.

## Existing capability boundaries

- `reasoning.py`, `planning.py`, `verification.py`: bounded candidates, model
  review, deterministic math, citation membership and authorized numeric Python
  checks. Planning checklists are explicitly non-executable; model review is not
  proof or calibrated confidence.
- `model_registry.py`, `task_router.py`, `orchestration.py`: exact-ID discovery,
  privacy/capability/context/cost filters, native/local-only modes, bounded retries,
  circuit breakers and limited collaboration. External credentials/account access
  were not exercised here. Historical family names do not grant access.
- `personal.py`, `storage.py`, `summaries.py`: user-owned notes/conversations,
  explicit summaries and shared FTS5 retrieval. Retrieval is lexical, not vector.
  Reserved private-document tables do not implement a retrieval service;
  `PlatformConfig.memory_enabled=True` deliberately raises an error.
- `runtime.py`, `task_store.py`, `event_bus.py`: one supervised worker, durable
  tasks/events, fencing, cancellation and exact-action approval. Only chat and
  explicit fixed diagnostic steps run. This is not an autonomous model/tool loop,
  DAG supervisor, user scheduler, executable skill learner or twelve-agent team.
- `execution.py`, `sandbox*.py`: owner/MFA capability grants; bounded offline
  diagnostics; narrow literal-IP TCP/TLS checks; isolated Python with no host
  fallback. No unrestricted shell or malware VM lab is installed.
- `browser.py`: opens local browser chat. It cannot navigate/extract pages or
  operate websites. `platform_repository.py` provides SQLite backup/canonical JSON,
  not repository indexing. `research.py` reconstructs checkpoint bundles, not a
  web research agent. Names were not counted as implemented functionality.
- Current text inference rejects image/audio content. Static logos, model-pack
  descriptions and model/dataset reference catalogs are not multimodal engines,
  installed models or training data imports.

## Independent native integrations

The original Hermes, OpenClaw and TradingAgents tracked source trees still match
their exact pins; [upstream-pins.json](upstream-pins.json) records fresh checks.
Independent environments, credentials, state and native implementations remain
separate. The bridge routes one selected backend per job and preserves uncertainty
receipts rather than broadcasting or blindly replaying actions.

| Runtime | Exact pin | Zenith integration limits |
| --- | --- | --- |
| Hermes | d05095663342556788cf2a198bfa7844cc7968ab | Native Runs API; owner-approved separate chat-only compatibility build for the 32K model versus native 64K floor. Bridge requires execution toolsets disabled. |
| OpenClaw | 2f5727b9c61c2ba9dccc3c880d9115f02cb8652f | Paired Gateway chat and exact approved report send; narrow optional provider compatibility plugin; device/browser/cron parity not enabled. |
| TradingAgents | e8f5503e9b86d5c2710b0c76b1f686703968c9df | Native financial research/risk graph in a separate service; REVIEW reports; no live-order endpoint or broker configuration. |

Historical native CI [40609634035](https://github.com/n8storm/Zenith/actions/runs/40609634035)
succeeded at `0a04cfc57bbed6056ae736e534d3db74a2492b81`, after the OpenClaw
answer-quality fix. This is historical acceptance, not a new four-runtime run or
a claim of 24/7 service availability today. Some older activation/compatibility
documents still describe the sidecar or fix as pending; see the current pinned
code and later CI, not those earlier snapshots, for implementation status.

## Findings and limitations

1. Grader validity is an immediate issue: fresh v1 diagnostics scored 11/14 and
   model-only 2/5, but observed failures include valid plural units and JSON
   whitespace. These are raw scorer outcomes, not validated general accuracy.
   Version a better suite; do not silently edit historical scores or train on
   mislabeled failures. See [BENCHMARKS.md](BENCHMARKS.md).
2. Dependency audit coverage is incomplete despite a zero advisory exit status:
   exact `torch==2.14.1+cpu` was skipped by PyPI lookup. Other 79 dependencies had
   no known advisories. Separate upstream 2.14.1 lookup also found none, but does
   not establish exact-wheel coverage. Integration locks and Node trees also
   need dedicated coverage. See [DEPENDENCIES.md](DEPENDENCIES.md).
3. GitHub main was unprotected at audit time. Development authorization and a
   successful CI run are not server-enforced branch approval rules. Protect the
   branch before automated Evolution publication. No repository settings changed.
4. There is no integrated Evolution observer/proposal/experiment/approval/canary
   state machine. Existing feedback/training gates should be extended, not
   bypassed or advertised as a complete self-improvement loop.
5. Full tracing/resource telemetry, scoped semantic/project memory, autonomous
   coding, MCP, desktop/browser automation, multimodal engines and specialist
   security workflows are incomplete or absent as mapped in the 40-row matrix.
6. Ops constraints remain: two CPU quota, 8 GiB memory, roughly 158 MiB initial
   disk headroom, no GPU, no provisioned persistent host. The systemd timer checks
   process liveness, not authenticated model readiness or extended availability.
7. Authorization is substantially implemented, but general roles beyond user/owner,
   external audit anchoring, complete retention automation and new plugin/agent
   policy administration still require work. Heuristic secret redaction and
   containers are not comprehensive leak/escape guarantees.

No exploitable remote compromise was demonstrated by this audit. That statement
does not certify absence of vulnerabilities. Proposed security work and open
questions are separated from demonstrated source/configuration findings in
[SECURITY.md](SECURITY.md).
