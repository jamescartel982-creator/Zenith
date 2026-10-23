# Changelog

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
