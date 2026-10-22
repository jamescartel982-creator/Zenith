# Quality goals, data, evaluation, and uncertainty

Zenith 0.6 adds a measurable improvement workflow. It does not establish that the small default model surpasses a frontier assistant or knows every subject.

## Defined task and baseline

The initial task is local educational chat: bounded arithmetic, basic science/history/finance explanations, and truthful handling of unavailable evidence and owner privileges. The public diagnostic suite is `agent/evaluation/suite-v1.json`. Its targets are no accuracy regression by existing slice, at least 30% lower warm median request latency, and zero owner-code disclosure. Authorization tests must all pass. These are initial development gates; extend them with representative tasks for your deployment before selecting a model.

```text
zenith benchmark --max-new-tokens 64 --output baseline.json
zenith benchmark --max-new-tokens 64 --output candidate.json --baseline baseline.json
```

Compare identical suite hashes, hardware, model revisions, token budgets, sampling settings, and warm-up policy. The report separates cold initialization, total answer time, first visible streamed text, and task slices. Model-generated cases are compared separately from arithmetic and evidence guards; those fast paths cannot be used to claim that the LLM itself became thousands of times faster. First visible text is word-buffered application output, not a low-level first-token GPU measurement. Output length, load, caching, and instructions still affect comparisons.

The 14 public cases were used during implementation. Rule-based keyword/abstention scoring can miss false extra claims and reject valid paraphrases. Reports preserve answers for error analysis. This is a development regression suite, not a blind generalization benchmark. It includes noisy Unicode arithmetic, unsupported current prices, missing historical evidence, and adversarial owner-privilege questions. Unit/API tests additionally exercise unauthorized access, secret rejection, invalid arithmetic, dataset leakage, and interrupted streaming. This does not establish general adversarial or demographic robustness; collect labeled deployment-specific edge cases and subgroup slices where applicable.

## Fast responses

**Fast** is the default. A configured team uses the first successful routed contributor, with bounded fallback; it skips cross-review and synthesis. **Thorough** runs the configured full process. The UI displays actual calls rather than implying every catalog model contributed. Ordinary Hugging Face, Ollama, and local-server answers stream as text becomes available. Thorough team answers appear after deliberation. Exact bounded arithmetic and a few explicit missing-evidence/authentication rules can answer without model generation.

The server allows one chat generation at a time and returns HTTP 429 when busy. Interrupted/failed partial answers are not stored as completed turns. Hugging Face cancellation joins the worker before allowing another request; a current native forward pass must finish. HTTP-provider cancellation may wait for a pending read timeout. Cold downloads and model loading can dominate the first request. CPU thread count is bounded by `ZENITH_CPU_THREADS`; use a suitable quantized local runtime or GPU for large packs. Streaming improves perceived responsiveness, not necessarily total inference throughput.

## Versioned data and isolated tests

`agent/resources/starter-v1.jsonl` contains 94 original, reviewed-for-this-example educational Q&A rows across ten topics. These authored fixtures are a starter experiment, not an expert-audited or representative global curriculum. Balanced preparation selects six per topic, producing 40 training, 10 validation, and 10 final-test examples:

```text
zenith curriculum sources
zenith curriculum prepare --balance-topics --output artifacts/curriculum-v1
zenith curriculum audit --output artifacts/curriculum-v1
```

Rows require IDs, source/revision/document provenance, topic, supported license, explicit `approved_for_training: true`, and alternating chat messages. Preparation normalizes duplicates, rejects conflicting answers and obvious secrets, groups shared documents and **every user prompt** transitively, and isolates those groups across train/validation/test. This prevents an earlier evaluation question appearing in a training conversation's context. Near-duplicates, paraphrases, correctness, coverage, and rights still require human review. SHA-256 manifests freeze the raw source snapshot and each partition; reusing a nonempty output directory is rejected.

Train only on `train.jsonl`, use `validation.jsonl` for development/selection, then evaluate the sealed final test once for the chosen experiment. The manifest-aware trainer reads test metadata to check overlap/hashes, never to construct optimization examples. The final test remains separate from the public answer-diagnostic suite. A fact may already exist in an upstream pretrained model: this isolation guarantee applies to Zenith's dataset version, not unknown upstream training.

## Training and broad resources

```text
zenith campaign --output artifacts/campaign-v1 --max-steps 40
```

Install the optional training dependencies first with your environment's `python -m pip install ".[train]"` from the checkout. This bounded command prepares balanced data, trains an adapter on a pinned base, evaluates final-test loss for base/candidate, compares generated-answer slices, and preserves logs/reports. Each phase runs separately to release model memory. It **never activates the adapter**, even if numeric checks pass. Inspect the answers, coverage, rights, and regression results before opting in with `ZENITH_ADAPTER`.

GitHub Actions also has **Bounded starter training candidate**, manually launched from Actions, with a 1–200 step budget and a 20-minute job timeout. It uploads the candidate, dataset, logs, and reports for 30 days. No paid model API key is used. This workflow is a reproducible experiment, not scheduled continuous self-improvement.

`sources-v1.json` records ten useful starting references: OpenStax, NASA, Smithsonian, MacTutor, Investor.gov, FINRA, OWASP, Python, Project Gutenberg, and scikit-learn. `source-checks-v1.json` records observed URL availability, titles, and prefix hashes. Reference metadata does not mean their content has been downloaded or used to train weights. Different pages/editions/assets can have different rights. Select material, retain notices/citations, check rights, clean it, and obtain subject review before adding training rows. No corpus of all books or every subject is bundled.

One bounded book importer is available:

```text
zenith import-book euclid
```

It snapshots the known Project Gutenberg Euclid/Casey HTML edition with original notices and a content hash, extracts bounded text chunks, and imports cited excerpts into the configured **shared retrieval index**. It does not download linked illustrations or train weights. Check the edition's terms and local public-domain rules. Existing dataset import and reviewed-chat export remain available; personal chats require explicit training approval.

## Calibration, abstention, and handoff

By default model answers are labeled **uncalibrated**, with no invented numeric confidence. Exact arithmetic is marked as verified by a bounded calculator. Missing live feeds, unsupported profit guarantees, secret requests, and precise dates without supplied evidence have explicit abstention rules. These conservative rules do not detect every unknown or every misleading source.

For a particular deployment, create an independent labeled calibration-validation suite and a different final-evaluation suite. Set `--purpose calibration-validation` for the former, then:

```text
zenith benchmark --fit-calibration validation-report.json --output calibration.json
zenith benchmark --suite independent-test.json --purpose final-test --calibration calibration.json --output calibrated-test-report.json
```

The optional artifact fits empirical **method-group** success frequencies and Wilson intervals, counting unique cases rather than repeated generations as independent evidence. It is an aggregate estimate, not an individual model probability. Fitting from a final-test report or evaluating on the fit suite is rejected. Reports include independent Brier score, expected calibration error, and coverage when supplied probabilities are available. Distribution shift can invalidate calibration; a handful of cases is insufficient for a production reliability claim.

Set `ZENITH_CALIBRATION_FILE` only to a locally reviewed artifact matching the exact runtime configuration. If the model-method group's lower confidence bound falls below `ZENITH_ABSTAIN_THRESHOLD` (default 0.6), Zenith abstains before generating/streaming a draft. Missing or mismatched artifacts are ignored and answers remain uncalibrated. No calibration artifact is enabled by default.

Signed-in users can explicitly **Request human review**, sharing that question and answer with the local server administrator. Responses are visible in **My human-review requests**. This is a real local queue; no external human is automatically contacted. Deleting the conversation removes its associated requests.
