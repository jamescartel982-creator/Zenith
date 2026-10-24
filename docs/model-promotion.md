# Model review, activation, and rollback

`zenith deployment` is a trusted local operator command. It is not exposed to the
model, browser chat, agent plans, or network clients. It changes a saved local
profile only after an explicit approval flag and real model loading.

## Activate the experimental checkpoint explicitly

```text
zenith setup --activate-candidate
```

From the cloned repository, this verifies the research bundle and evaluation
reports, reconstructs and caches the same trained adapter, downloads its original
pinned base if necessary, tests loading, and selects it in your saved profile.
This command explicitly accepts the recorded regressions. The receipt records
`activation_status: experimental`, `numeric_gate_passed: false`, and
`regression_override: true`; it never changes raw reports or marks failed scores
as passed. The approved-release workflow retains its original quality gate.

The lower-level operator command is:

```text
zenith deployment use-research --bundle research_checkpoints/recovery-v1 --approve --allow-regressions --download-base
```

For another verified checkpoint, `deployment activate` also accepts
`--allow-regressions` together with `--approve` and a review note. This exception
only permits measured quality regressions. Changed weights, forged scores,
incomplete evidence, protocol differences, or incompatible tokenizers still fail.
Neither command is exposed as a chat or remote execution tool. One checkpoint is
selected at a time. Activating a different version preserves the prior profile
for rollback; it does not average unrelated models or grant security capabilities.

The cached model and evidence survive moving the source checkout. Use
`zenith deployment status` to locate its receipt and the rollback command below
to restore the previous profile. Existing environment variables and checkout
`.env` settings still take precedence over saved configuration.

## Review a candidate

Measure the complete fixed diagnostic suite on the candidate, its immediate
trained parent, the previous trained reference, and the production base with the
same generation settings. Keep the reports and checkpoints unchanged. Also review
independent transfer probes, held-out loss, and raw answers: these small public
diagnostics are development checks, not expert certification.

```text
zenith deployment review --candidate NEW_CHECKPOINT --candidate-report CANDIDATE_REPORT --baseline-report IMMEDIATE_PARENT_REPORT --baseline-report PREVIOUS_TRAINED_REPORT --baseline-report PRODUCTION_REPORT --output NEW_REVIEW.json
```

The command recomputes every result from the saved answer and original scorer.
Missing cases, altered prompts, inconsistent scores, mismatched token budgets or system instructions,
different base/tokenizer identities, and changed candidate files fail validation.
Both production and the immediate trained parent must be represented. A slice
regression against any supplied baseline fails the numeric gate even when overall
accuracy improves. Individual previously passing cases also must remain passing;
gaining a different case in the same slice cannot hide a regression. A failed
review returns a nonzero exit status.

Scoring version 3 fixes two false negatives: a correct `x = 5.` answer and an
initial `No.` answer may end with sentence punctuation. Wrong numeric values,
incomplete algebra, and fenced or malformed JSON still fail. Historical raw
reports are preserved; all comparison baselines must be rescored with the same
version using `zenith expansion-eval --rescore-input OLD_REPORT --output NEW_REPORT`.

## Explicit local activation

```text
zenith deployment activate --review NEW_REVIEW.json --approve --review-note "Reviewed raw answers and independent evaluation; owner approved activation."
zenith deployment status
```

Activation rechecks the evidence and loads the actual adapter with its original
pinned base and compatible tokenizer. It saves a private backup of the entire
previous configuration, writes an immutable deployment receipt, and atomically
updates the profile. It preserves unrelated settings. Checkpoints and training
reports are never overwritten. A training report's original `promoted: false`
describes its state at creation; subsequent activation is recorded separately.

Restart Zenith to load the selected checkpoint. The profile selects Hugging Face
inference and records `ZENITH_ADAPTER`, `HF_MODEL`, `HF_REVISION`, and
`ZENITH_CHECKPOINT_RECEIPT`. Explicit environment variables or a checkout `.env`
take precedence; remove conflicting overrides deliberately. At model load, the
receipt pins all checkpoint file hashes and the base revision. Changed files or a
rolled-back receipt cause an error before inference.

## Source-release bundles

An approved model bundle can contain the adapter, tokenizer, training history,
frozen diagnostic evidence, and a `release.json` file inventory. Activate it with:

```text
zenith deployment use-release --bundle PATH_TO_BUNDLE --approve --download-base
```

The command verifies every bundled file, copies the bundle into stable user
storage, rebuilds the promotion decision from raw answers, and performs the same
loading and profile checks. An existing cached release is verified and never
overwritten. Moving or deleting the downloaded source folder does not remove the
cached model. No provider API key is involved. `--download-base` caches the verified
release's original pinned base; omit it when the base is already cached. Offline
mode is respected.

For a bundle distributed with a source release, installation can explicitly
select it using `bash install.sh --activate-release PATH_TO_BUNDLE --launch` on
Linux, or the same `--activate-release PATH_TO_BUNDLE --launch` arguments to
`install.ps1` on Windows. Existing installations keep their configured model
unless this option is supplied. Setup caches the base before validating the
selected adapter.

## Rollback

The activation output contains an `id`. Its receipt lives under the Zenith user
directory in `deployments/ID/receipt.json`.

```text
zenith deployment rollback --receipt PATH_TO_RECEIPT.json
```

Rollback verifies the current profile and backup hashes, restores the exact
previous profile, and records the rollback. It refuses to overwrite intervening
profile edits. Restart Zenith afterward. If there was no previous profile,
rollback removes the newly created profile.

Model activation does not enable restricted security tools, grant capabilities,
change MFA, or bypass authorization and target scopes. These remain separate
[server-side execution controls](execution-controls.md). Local audit files are
operational records, not tamper-proof signatures against a hostile OS owner.
