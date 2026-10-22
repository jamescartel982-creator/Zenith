# Public development evidence

These reports preserve actual outputs, including failures. See [validation notes](../../validation.md#streaming-quality-workflow-and-owner-tools-06) for interpretation.

- `baseline.json`: recorded v0.5 direct-model requests before the upgrade, temperature 0, no streaming.
- `controlled-fast.json`: v0.6 base model, same sampling/budget/revision, streaming and deterministic gates.
- `controlled-candidate.json`: the unpromoted starter adapter compared with that base profile.
- `training-report.json`, `test-baseline.json`, `test-candidate.json`: real training and final-test loss measurements.
- `frozen-pilot-dataset/`: exact original public starter source and grouped partitions used in that pilot. Hashes verify with `zenith curriculum audit --output docs/benchmarks/v0.6/frozen-pilot-dataset`.
- `browser-report.json`: real CPU memory/streaming and owner/review browser checks.
- `euclid.json`: bounded source-linked book import report. The full HTML book and weights are not stored in Git.

The public answer suite was used for development. Keyword scoring has false positives/negatives and does not certify complete factual correctness. Five model-generated cases are reported separately from nine built-in paths. Faster overall median requests do not imply faster raw LLM inference. The candidate was not promoted, and no broad competence claim follows from loss on ten final-test examples.
