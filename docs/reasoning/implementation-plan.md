# Phase 3 implementation and compatibility

Parent: `e6963d9c6f45c196ae2e301819ae1ae093b35c41` (merged PR #17). The 243-test baseline and all seven Windows/Linux/container CI checks passed before this branch. Existing checkpoint/tokenizer hashes and trained lineage remain recorded in `docs/platform-audit`. This phase adds no training, adapter promotion, profile migration or model download.

Dependencies: use the registry/provider adapters and shared routing budgets from Phases 1–2; use existing exact arithmetic, SQLite evidence and owner/MFA execution controls. Keep existing chat and routing unchanged unless the new reasoning provider/command is explicitly selected.

Implementation order:

1. Structured, bounded task checklists and adaptive Fast/Standard/Deep/Research call budgets.
2. Independent answer candidates, separate critique, deterministic arithmetic checks and source-attribution checks. Reviews remain fallible and uncalibrated; source attribution alone does not prove claim truth.
3. A single bounded correction/recheck cycle. Every stage shares the original deadline, call count and provider-cost ceiling. Failed deterministic checks cannot be relabeled as successful model critique.
4. Owner/MFA-only `verify-python` capability: execute a deliberately restricted numeric Python AST subset in a separate isolated-interpreter process with bounded source, steps and wall time. No arbitrary Python, imports, attributes, file/network primitives, shell, user recursion or loops. This is not a general-purpose OS sandbox; unsupported programs are rejected explicitly. Ordinary chat cannot activate or invoke it.
5. CLI/provider integration, frozen diagnostic fixtures, real unchanged-checkpoint inference, focused unit/security/integration tests, Windows/Linux installed CI, documentation and review PR.

Do not claim GSM8K/HumanEval+/SWE-bench performance from the small authored diagnostic suite. Measure and publish raw model outputs and accuracy separately from deterministic verifier outcomes. Phases 4–15 remain planned after Phase 3 review.
