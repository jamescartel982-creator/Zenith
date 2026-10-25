# Changelog

## 0.15.0 — Optional model registry and native-first orchestration

- Harden routing consent and budgets, validate provider capability metadata, prevent retries of revoked access across long collaboration stages, and preserve uncertainty on contradictory reviews.

- Audit the complete tracked source inventory, verify the existing trained adapter and tokenizer, and record the unchanged 208-test baseline.
- Add trusted provider adapters, exact account model discovery, conservative capability/lifecycle metadata, and explicit external model opt-in.
- Integrate bounded routing, independent drafts/synthesis, model review, cooperative deadlines, cancellation, fallback and circuit breakers with existing providers.
- Preserve model provenance and exclude external-output conversations from training export. Keep restricted tool execution behind existing MFA, grants, scope and emergency stop.
- Preserve the original model, tokenizer, checkpoints, profiles, data and Git-clone installation flow. No retraining, model promotion or later-phase capability is claimed.

## 0.14.1 — Terminal installation options

- Restore the Git clone, `install.py --mode local`, and terminal-chat launcher instructions as the primary setup flow; keep the standalone bootstrap optional.
- Add a standalone standard-library bootstrap that downloads the official source archive, verifies its complete release inventory, and runs the existing isolated installer.
- Provide one terminal command for Windows and Linux with no Git or manual environment activation. Support custom folders, installation without launch, and explicit experimental candidate selection.
- Resume verified existing installations without overwriting local code, settings or data; reject unsafe or corrupted archives before running source code.
- Exercise bootstrap stdin execution and the actual install path on both operating systems.

## 0.14.0 — Explicit candidate activation and conventional installation

- Add `zenith setup --activate-candidate` and an explicit experimental deployment override. Preserve failed numeric scores in the activation receipt instead of marking them passed.
- Verify and cache the complete research bundle, reconstruct the exact adapter, load it with the original tokenizer and pinned base, and preserve profile rollback. Restricted security tool grants remain separate.
- Bundle frozen evaluation evidence with the experimental snapshot for reproducible activation outside the original checkout.
- Lead installation with standard Git, venv, pip, setup, and serve commands for Windows and Linux; retain optional launchers and existing settings.
- Exercise real installed candidate activation, inference, and exact rollback on Windows and Linux.

## 0.13.0 — Regression repair and reversible model activation

- Continue the existing trained checkpoint using authored repair curricula, historical training-only replay, and reviewed preference examples. Preserve architecture, tokenizer, original checkpoints, and raw evaluation evidence.
- Correct punctuation-related false negatives consistently across saved baselines; reject edited/incomplete reports, different evaluation protocols, slice regressions, and individual case regressions.
- Add explicit local model review, stable release caching, real load/inference checks, checkpoint-bound runtime receipts, exact profile backup, and rollback. Restricted execution permissions remain separate and disabled by default.
- Support an explicit installer `--activate-release` option, original pinned-base caching, and installed-provider release checks on Windows and Linux.
- Include an inactive, byte-inventoried research checkpoint with actual learned weights, original tokenizer, and real Windows/Linux loading checks. Keep it out of production activation and container images.
- Record that automated diagnostic success alone does not establish deployment readiness. Independent transfer results and manual answer review remain required.

## 0.12.1 — Diagnostic grading and promotion validation

- Accept sentence punctuation after a completed correct algebra answer and an initial negative authorization answer, while retaining wrong-number and structured-output checks.
- Recompute scores from complete raw reports and reject altered evidence, mismatched token budgets/system instructions, and model/tokenizer identity differences.
- Prevent individual case regressions from being hidden by unchanged category averages. Preserve original reports during explicit rescoring.
- Document measured recovery progress and remaining blockers without publishing or activating an unapproved model.

## 0.12.0 — Verified continuation and owner execution controls

- Verify and continue an existing trained adapter without initializing a new foundation, replacing the architecture, or changing token IDs. Preserve parent hashes and separate all candidate outputs.
- Add SFT, corpus continuation, validated-preference DPO paths, historical replay isolation, raw-model diagnostics, candidate review campaigns, and local merge/reload export verification.
- Record the actual CPU experiment and frozen evidence. Lower held-out loss did not pass all answer/retention gates; candidate weights remain unpromoted and unpublished.
- Migrate account passwords to Argon2id on successful login, add encrypted TOTP enrollment and replay prevention, and require MFA plus explicit scoped grants for restricted execution.
- Enforce target scopes and short-lived capability access on both new and legacy diagnostic routes; add activity logs, bounded plans, emergency shutdown, and trusted local owner recovery.
- Preserve existing memory/retrieval and add explicit account-owned conversation summaries. No summary or ordinary conversation updates neural weights.


## 0.11.1 — Simple setup and launch

- Add Windows double-click installation and launch scripts, plus a Linux start script. Normal use automatically selects the private environment.
- Add installer `--launch` to download configured Hugging Face weights and open browser chat after successful setup; retain existing external-runtime profiles.
- Open the browser only after the launched server is ready, with a manual URL fallback and clean handling of setup interruption or launch failure.
- Put ZIP-based Windows setup and a single Linux install-and-open command first in the README. Keep advanced activation and runtime options available.


## 0.11.0 — Model discovery, pixel identity, and explicit environments

- Add public Hugging Face and GitHub discovery with pagination, published fine-tune lineage metadata, bounded requests, caching, offline handling, and explicit source failures.
- Save selected model source metadata into the operator's local library and make it searchable in the catalog. Runtime configuration remains explicit; no repository code or weights are downloaded by discovery.
- Add an original white pixel Zenith banner inspired by the supplied reference. Bundle it in browser welcome and persistent header branding; share a terminal wordmark between installation, chat, and owner login.
- Rewrite the README around installation, workspace behavior, model discovery, privacy, and verification, without model-inventory marketing totals.
- Provide PowerShell and Bash activation helpers. Require the installer's selected interpreter to be isolated before pip operations, and clarify successful dependency checks while retaining real failures.


## 0.10.0

- Add built-in `/skill list`, `/skill ID`, `/skill status`, `/skill off`, and `/skills` commands in browser and terminal chat. Commands bypass inference and are excluded from chat/training history.
- Persist selection per conversation in an additive SQLite table; resolve chat selection on the server and protect reads/writes with conversation ownership.
- Restrict all 16 cybersecurity profiles to the configured owner with a valid login and current admin-code elevation. Check authorization in the core and both chat endpoints; reject forged fields and non-owner access.
- Bind protected selection to the login hash and clear it on lock, logout, code rotation, re-unlock, or expiry. Recheck before model work, at streamed chunks, and before saving; revoked partial turns are discarded.
- Add masked `/admin unlock` and `/admin lock` controls to terminal chat with temporary-login cleanup. Browser commands open the existing private Admin field; secrets are never command arguments.
- Remove 24 AI engineering subjects from the runtime catalog and preserve their development guidance/reference bibliography in `docs/engineering.md`. The application now has 11 public conversation skills, 16 owner-only security profiles, and 24 associated references.
- Add authorization, command, persistence, revocation, terminal, and upgrade tests; update README, owner instructions, API documentation, and release checks.

Account-level authorization does not sandbox the local OS owner. Skills remain bounded model guidance; this release adds no offensive execution tools, weights, or training. Optional calibration artifacts must match the new release signature.

## 0.9.0

- Add a curated, packaged learning library: 51 versioned profiles (24 AI, 16 cybersecurity, 11 general subjects), 40 original-source references, and six educational hacker-color explanations.
- Give each profile a workflow, deliverable, review checklist, practice exercise, and linked resources. Cybersecurity profiles focus on defense, evidence, remediation, recovery, and authorized non-destructive assessment planning.
- Add a searchable desktop/mobile Skills dialog and grouped chat selector; add offline `zenith skills list/show/resources/taxonomy/validate` commands.
- Validate resource provenance, HTTPS links, schema bounds, categories, and references; isolate returned metadata from the cached library. Apply only the selected profile to a request.
- Preserve existing general-subject prompts; keep detailed security scope guidance within cybersecurity and AI-security profiles.
- Record original-publisher page retrieval dates and status; resource browsing/selection performs no external fetching, training, tool execution, or role elevation.
- Add library/API/CLI/integration tests and installed-wheel/CI validation. Refresh the README, skill inventory, resource bibliography, and release manifest.

Learning references are curated rather than exhaustive. Prompt guidance does not guarantee model compliance or establish expertise, and external sources retain their own terms. New model weights or training are not part of this release; optional calibration artifacts must match its release signature.

## 0.8.1

- Require explicit Ollama/local-server stream completion before an answer is persisted. Interrupted or malformed replies emit an error and retain no partial training/history turn.
- Extract bounded HTTP framing into a separate module with strict UTF-8/JSON handling, NDJSON, multiline SSE, CR/LF/CRLF boundaries, comments, and frame/stream byte limits.
- Read arriving bytes without waiting for a larger line buffer to fill. Verify first-text delivery with a real HTTP server that waits for the client before sending the remainder.
- Close HTTP responses on success, failure, cancellation, and early termination; block Ollama redirects as well as local-server redirects.
- Validate text and completion metadata, retain provider token counts only after successful completion, and reject unsupported tool-call finishes.
- Add protocol and real HTTP regression tests for partial-turn rejection, model-lock recovery, cancellation, Unicode, malformed payloads, and bounded parsing. Refresh the README and release inventory.
- Run branch validation on pull requests and post-merge validation on main, avoiding duplicate push/PR jobs for the same feature branch.

This is an application reliability update. It changes no model weights or training and makes no general inference-speed or intelligence claim. Optional calibration artifacts must match the new release signature.

## 0.8.0

- Add a complete tracked-source SHA-256 manifest and `zenith verify --source PATH`, usable on extracted ZIPs without Git. Text checks normalize Windows/Linux line endings; binary checks are exact.
- Add installed-wheel file verification, with clear handling of editable installs, missing/modified files, and code/metadata mismatches.
- Centralize version metadata across packaging, commands, health, System, and calibration signatures.
- Install the Zenith command in Docker; include documentation, sample configurations, attribution, and all vendored support files. Keep local secrets and model weights out of the image.
- Persist container owner-code/profile storage in the data volume, forward response-budget settings, and pin the default primary revision.
- Make Fast-mode inference diagnostics call one real contributor without requiring the unused reviewer's cache; Thorough retains complete-team checks.
- Refresh README upgrades, account/API deployment guidance, team documentation, and native/container checks.

No new weights or training improvement is claimed by this maintenance release. Existing v0.7 speed results retain their original scope. Older optional calibration artifacts need refitting because release signatures change.

## 0.7.0

Five-component System view; private performance aggregates; owner-only server totals; Auto/Brief/Full budgets; compact prompts and bounded recent context; cached-weight reuse; terminal streaming; optional warm-up; browser Stop/continuation; ASGI disconnect cleanup; scheduled and PR diagnostic checks.

## 0.6.0

Streamed replies, Fast/Thorough routing, exact bounded arithmetic, abstention, instruction profiles, account-bound owner elevation, private generated codes, bounded Devil-mode tools, human review, versioned grouped train/validation/test preparation, training campaigns, calibration contracts, and cited book retrieval. A small completed LoRA pilot stayed unpromoted after answer review despite lower fixture loss.

## 0.5.0

Password accounts, welcome-back greetings, private memories, conversation navigation, branding, and safe Markdown. Three requested model packs inventory all 132 files and vendor 43 support/source files; 89 weight variants remain external verified downloads.

## 0.4.0 and earlier

Working open-model and scratch-transformer paths, reviewed exports, bounded collaboration, sourced 1,000-model/200-dataset metadata, Windows/Linux installation, and Docker deployment.
