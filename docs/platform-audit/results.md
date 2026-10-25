# Phase 1–2 validation

Audit baseline: `2dc28c03227cf5f2b04beea263195133a485193e`, 208 tests passed, one optional skip, 27.930 seconds. Trained checkpoint loaded exactly through the existing checkpoint verifier; native model response `4`. Exact artifacts, architecture and framework versions: [baseline.json](baseline.json).

## Focused validation

Phase 1: 11 new tests passed, 3.565 seconds. Tests exercise actual local HTTP adapter round trips, bounded paginated discovery, exact account IDs, retired/unknown capabilities, credential absence, sanitized errors, rejected tool outputs and local endpoint boundaries. These are protocol integration fixtures, not simulated claims of live account access.

Phase 2: 17 focused tests cover native/local-only privacy, measured routing, explicit context/modality/tool/cost filters, independent drafts and synthesis, bounded retries/circuit breakers/fallback, cancellation/deadline propagation, invalid review uncertainty, actual SQLite chat provenance/retrieval/training-export filtering, and real owner login + Argon2id/MFA + scoped grants + revocation/emergency-stop authorization. No tool is executed by routing itself; no secret enters the model messages.

## Actual unchanged-model inference

[native-inference.json](native-inference.json) records a live original-vs-orchestrated comparison using the same loaded, unchanged adapter and deterministic 32-token limits on CPU. Cold load: 5.526 seconds. Arithmetic: `4` on both paths (737.847 ms original, 742.870 ms routed). Geography: `Paris` on both paths (682.508 ms original, 571.788 ms routed). One warm observation per prompt/path; no statistically supported speed improvement is claimed. This is two-probe harness compatibility, not a general reasoning or instruction-following benchmark. Routed answers are buffered; these latencies are not streaming TTFT.

Original adapter inventory and saved configuration were hashed before and after: unchanged. Research bundle inventory verifies. No training, checkpoint export/promotion, API distillation, external paid inference or production profile changes occurred. The existing experimental checkpoint's failed numerical promotion/retention gates remain failed.

## Boundaries and remaining work

External credentials were absent, so OpenAI/Anthropic account discovery and generation remain live-unverified. Supported API protocol behavior is tested on real local HTTP sockets. Claude family references do not grant restricted account access. Only text execution is implemented here; vision/audio/image generation, MCP, coding execution, multi-query web research, local interpretability and new benchmark suites belong to the later explicitly planned phases.

CPU-only environment: GPU utilization/VRAM unavailable. Provider billing and cost per task were not measured. No scores are supplied for GSM8K, HumanEval+, SWE-bench or multimodal evaluations. Numerical quality regression/retention evidence is preserved from earlier training; this work does not make a new quality-gate pass claim.

## Full local regression run

All **236 tests passed**, one optional skip, in **34.341 seconds** on Linux/Python 3.12. This includes all 208 baseline tests and 28 new tests. The release source inventory covers all tracked files except itself. Native Windows/Python 3.10/3.12, installed inference/rollback and container checks run through GitHub CI; CI outcomes must be read from the PR rather than inferred from this Linux run.

A second full run passed all 236 tests (one skip) in 30.773 seconds. The regular `zenith_local-0.15.0` wheel was installed into a separate environment and executed with Python isolated mode outside the source checkout: installed file verification passed (116 files), then actual original/routed model inference matched on both probes and confirmed unchanged weights/profile. The terminal `route --mode native` returned `Paris` with the exact Hugging Face model identity. Original `doctor --inference` and real server startup/health/UI smoke checks also passed. Source release verification passed all 373 inventoried files before publication.

## Phase 1/2 review follow-up

Rechecked PR #17 at `5585b1e323980501519e3240299b4c133c31ea60`: the fresh 236-test baseline passed with one skip in 28.843 seconds. Seven new regression tests reproduced malformed privacy/budget inputs, invalid provider capabilities and measurement values, stale access-denied routing after a long fallback, and contradictory review acceptance. The fixes reject ambiguous flags/metadata, recheck live eligibility before each stage and retain concerns when a review lists issues. The updated **243-test suite passed**, one skip, in **35.590 seconds**.

A fresh actual original/native-orchestrated comparison is recorded in [native-inference-hardening.json](native-inference-hardening.json): both paths returned `4` and `Paris`, with exact matching outputs, unchanged checkpoint inventory and unchanged saved configuration. No new training, model promotion, credentials or external API access were involved. This follow-up remains within Phases 1–2; later phases are not represented as implemented.
