# Diagnostic grading and promotion checks

Scoring version 3 corrects two false negatives: a completed `x = 5.` answer and
a valid initial `No.` may use sentence punctuation. Wrong numeric values,
incomplete algebra, and fenced or malformed JSON still fail. The 24 diagnostic
questions and expected answers are unchanged.

The promotion comparison recomputes every saved score. Missing, duplicate, or
reordered cases, altered prompts, inconsistent totals, different token budgets,
different system instructions, incompatible model/tokenizer identities, and old
scoring versions are rejected. Every previously passing individual case must
remain passing; improvement elsewhere cannot hide a regression inside an average.

Preserve old reports and rescore all comparison baselines with the same version:

```text
zenith expansion-eval --rescore-input OLD_REPORT.json --output NEW_REPORT.json
```

The command refuses to overwrite an existing output and records the original
report hash. It changes neither checkpoint weights nor raw generated answers.
Historical reports in this repository remain unchanged.

## Recovery status observed in the working session

These observations are experimental, not an approved model release. Trained
checkpoint artifacts and complete follow-up reports still await upload from the
execution workspace.

- A continued-training candidate reached 24/24 on the public automatic diagnostics.
- The same candidate scored 16/18 on the first transfer probes, versus 9/18 for the
  previous trained checkpoint. A retained science fact regressed.
- New-curriculum held-out target loss fell from 0.9715 to 0.1052; previous-domain
  target loss rose from 3.2076 to 3.4212.
- Raw review found misleading permission-bypass and approval-state wording that
  keyword checks had accepted. The 24/24 score did not authorize activation.
- A 64-step preference repair scored 20/24. Same-lineage parameter averaging
  recovered an automatic 24/24 but retained misleading permission wording.
- A separate evaluation using explicit application-policy instructions was
  interrupted when the execution environment disconnected. No result is claimed
  for that interrupted evaluation.

The latest locally completed infrastructure snapshot passed 197 tests with one
platform-specific skip before the interrupted application-policy check. This
GitHub patch is a smaller, independently CI-validated grading update; it does not
claim that all pending runtime changes or model artifacts have been published.

Candidate selection used public development diagnostics, so these numbers are not
a sealed estimate of general intelligence or expert cybersecurity competence.
Automatic promotion remains disabled. The production checkpoint, original
tokenizer, existing account/memory systems, and restricted-tool controls are
unchanged.
