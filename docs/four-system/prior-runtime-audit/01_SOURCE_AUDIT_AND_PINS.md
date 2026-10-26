# Source audit, exact pins and preservation

**2026-10-26 — audit/proposal only.** No existing source, model, tokenizer, adapter, configuration or native state is changed. Existing upstream features remain owned by their original runtimes. S = source evidence; D = documentation claim; M = actual measurement; P = proposal. Source presence is not live interoperability or feature-parity verification.

| Repository | Pinned commit | Local source copy |
| --- | --- | --- |
| n8storm/Zenith | f1dbab49f915d4c74b57e560aafac7e51efde373 | /workspace/zenith-runtime-bridge-audit-20261026/zenith |
| NousResearch/hermes-agent | d05095663342556788cf2a198bfa7844cc7968ab | /workspace/zenith-runtime-bridge-audit-20261026/hermes-agent |
| openclaw/openclaw | 2f5727b9c61c2ba9dccc3c880d9115f02cb8652f | /workspace/zenith-runtime-bridge-audit-20261026/openclaw |

These are three fresh separate Git clones of previously fetched public repository snapshots, checked out detached at the exact pins. They are not claimed to be the latest upstream HEAD. The original checkouts remain present. Full tracked source, tests, configuration, lock/manifests and license files are retained in each native tree. Later reference commits require a delta audit. Local clone origins are snapshot locations; the canonical repositories and SHA/tree identities are recorded in [pinned-sources.json](../evidence/pinned-sources.json).

| Tree | Tracked paths | Python paths / parse failures | Test-named paths (not executed tests) | Plugin manifests / skill paths |
| --- | --- | --- | --- | --- |
| openclaw | 59647 | 64 / 0 | 26582 | 184 / 128 |
| hermes | 21255 | 10208 / 0 | 9271 | 108 / 211 |
| zenith-main | 518 | 169 / 0 | 64 | 0 / 0 |

The compressed `*-source-index.jsonl.gz` artifacts inventory every tracked path with SHA-256, size or symlink target, Python imports/top-level symbols and TS/JS import/export anchors where applicable. This is a **file-by-file structural audit**, not a claim that every dynamic branch was manually proven correct. AST parsing used Python3.12 and does not establish Python3.14 runtime support. Regex JS/TS anchors do not replace typechecking or a complete semantic call graph. Test-named counts include helpers and fixtures. Archived audit Python files in Zenith are indexed as files, not classified as active production modules.

## Current Zenith, preserved

Zenith main is 0.17.2. Its Agent, provider registry/reasoning, personal memory, owner/MFA/capability grants, supervised tasks, Docker execution, training/review/checkpoint and deployment owners remain intact. Sources include [agent/core.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/core.py#L1), [agent/providers.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/providers.py#L1), [agent/personal.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/personal.py#L1), [agent/runtime.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/runtime.py#L1), [agent/continual.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/continual.py#L1), [agent/deployment.py:1](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/deployment.py#L1).

The selected trained artifact is the existing Qwen2ForCausalLM base Qwen/Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`, with its existing rank8 LoRA: 494,032,768 base parameters, 4,399,104 adapter parameters, 24 layers, hidden896, architecture ceiling32768, tokenizer151665 (embedding vocabulary151936). This is the existing Zenith identity/lineage, not a replacement. Actual usable context/output remains the configured inference budget. The [public prior model inventory](../evidence/zenith-model-verification.prior.json) and [current protection checks](../evidence/model-profile-preservation.json) are separate evidence; no random initialization or training occurs here. The selected adapter retains its existing experimental status and failed numerical gates; a working inference probe is not a quality promotion.

## Public endpoint gap

[agent/server.py:499](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/server.py#L499) and [agent/server.py:519](https://github.com/n8storm/Zenith/blob/f1dbab49f915d4c74b57e560aafac7e51efde373/agent/server.py#L519) expose Zenith's custom chat API. The source route audit found no raw OpenAI-compatible `/v1/chat/completions` model service. Existing custom SSE/chat payloads cannot be relabeled as that protocol. Under the user's Phase4, a separate additive inference adapter requires approval before implementation. Existing provider generation can be reused at its pinned interface; no model implementation, tokenizer, weight or existing server route is to be changed.

## Approval / no-change boundary

This delivery writes reports and audit tooling outside all three source roots only. No upstream install/update script, service or platform integration was launched. No GitHub code/PR/branch, native config, credential, database, model or production service is changed. See the incompatibility decisions and proposed file plan before approving any new inference/bridge deployment.
