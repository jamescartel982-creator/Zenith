# Preservation, backup and rollback

**2026-10-26 — audit/proposal only.** No new bridge, model endpoint, service, profile, credential or deployment has been enabled; existing native code/configuration/state remains unchanged.

Retain all three exact pins and tracked file hashes, original configurations/permissions/services and model/adapter/tokenizer identities. Installation may create only a new sibling overlay, separate environments and explicitly named integration profiles/services. Originals are never replaced, reset or deleted.

Back up each native store with its supported consistent mechanism and schema/version/keys. SQLite needs a WAL-consistent backup, not copying a live .db alone. OpenClaw control-plane/agent/credential stores remain distinct; Hermes profile state, jobs, memory, skills and secret scopes remain native; Zenith keeps its accounts/conversations/memory/training/checkpoints. The bridge ledger stores control mappings/receipts, not a merged memory DB.

Rollback sequence:

1. Stop new bridge admissions and newly owned external ingress; revoke bridge grants/service credentials and preserve task/session/delivery facts.
2. Cancel/pause/drain native work through supported interfaces; stop specifically owned services/containers when required. Record unknown external outcomes instead of resending elsewhere. Do not stop unrelated original services.
3. Disable the new portal/bridge/inference startup registrations. Original sources, profiles, CLIs/UIs and inference remain available.
4. Retain new state/receipts for reconciliation. Removing the overlay must not discard original or newly accumulated user history.
5. Use an older deployment only if native schema/read/write compatibility is proven. Otherwise forward-repair or perform explicit recovery preserving newer data; never restore an old DB over new writes silently.

No model merge, tokenizer conversion, training, original activation change or quality-score override belongs to bridge rollback. The active adapter's experimental gate results remain recorded. Any later model candidate uses its separate evaluation/approval workflow.

Native updater implementations remain intact. Immutable live pins are updated through new candidate copies/environments, original tests, backup/restore and explicit promotion. In-place self-update of the same deployed tree conflicts with immutability; obtain a decision instead of patching or silently disabling it. No rollback was needed in this audit because original implementations/configuration/services were unchanged. Private profile/hash receipts are excluded from public delivery.
