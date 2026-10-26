# Explicit incompatibilities and approval decisions

**2026-10-26 — audit/proposal only.** No new bridge, model endpoint, service, profile, credential or deployment has been enabled; existing native code/configuration/state remains unchanged.

| ID | Constraint | Required preservation-compatible decision |
| --- | --- | --- |
| D01 | Zenith lacks raw compatible inference; user Phase4 requires adapter approval | Approve the new external inference service/contract modules only; no existing server/provider/weight/tokenizer/config edits. Not implemented. |
| D02 | Existing profiles unchanged versus defaulting upstream provider to Zenith | Create distinct approved integration profiles. Attaching/changing originals needs a concrete config diff; never overwrite/copy credentials automatically. |
| D03 | Immutable live source pins versus original in-place updater behavior | Keep native updater intact; use candidate-copy version promotion. Literal in-place update and same immutable pin conflict and need a decision. |
| D04 | Complete native tools versus restrictions on untrusted shell/credentials | Supported native policy plus independent runtime isolation; ingress auth alone is insufficient. Unsupported enforcement stays blocked or requires explicit source-patch approval. |
| D05 | No existing Zenith edits versus automatic current-installer/UI/manifest integration | Recommend separate sibling overlay with its own entry point/lock/checksums/portal. Existing installer/UI/source-manifest edits need approval; none made. |
| D06 | Connect every picture node versus private helpers/SDKs | All55 labels mapped; keep memory/context/SQLite internal to native runtimes, not invented bridge endpoints. |
| D07 | Per-user least privilege versus OpenClaw shared-secret HTTP owner authority | Paired/scoped WS and isolated profiles/runtimes; no fake narrow header over an owner token. |
| D08 | Full original baselines versus missing supported environments/dependencies | Provision separate compatible test environments/storage. No changed tests, dependency merge or fabricated pass. Baselines remain BLOCKED. |
| D09 | 24/7 operation versus no always-on deployment target | Deliver owned-supervisor/state/health/backup/soak design; select/provision a host and pass actual acceptance before enablement. |
| D10 | All native tool/media features versus current text-model limits/experimental quality | Validate actual context/tool-history/schema/media compatibility. No fake capabilities, silent truncation or substitute foundation model. |
| D11 | One shared model object versus unchanged original Zenith app config | External runtimes share new exact-artifact inference; original app may keep its own model instance. Consolidation needs approved config/resource tests. |
| D12 | Every plugin/channel/device versus absent source/licenses/accounts/devices | Track individually; source catalog does not install or grant access. Supply prerequisites, approve an alternative, or retain explicit blockers. |
| D13 | Uniform global admin/revocation across original native UIs/jobs | Native entry points keep native trust; separate ownership, real approvals/cancel/stop/isolation required. No prompt-level admin impersonation. |

Reviewable approval requested after these deliverables: **approve the new external Zenith inference adapter and sibling bridge workspace/new integration profiles while leaving existing source/config/model artifacts untouched.** This does not waive baseline/security/quality/release gates or authorize an undisclosed upstream patch. Any unavoidable later native source/config modification must be presented separately before implementation.
