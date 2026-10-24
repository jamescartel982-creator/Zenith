# Continued-learning recovery study

This study starts from the latest verified trained adapter from the 0.12 pilot.
It keeps the original Qwen2 architecture, pinned base, tokenizer, and learned
adapter values. Each stage loads its trained parent and saves a new directory;
original files are checked for changes. No unrelated foundation model is used.

## Recorded development results

The same 24 questions, expected answers, greedy generation, and 48-token output
budget are used throughout. Scoring version 3 fixes false negatives for sentence
punctuation after `x = 5.` and a valid initial `No.`. Wrong numbers, incomplete
algebra, and fenced or malformed JSON still fail. Historical reports are
preserved; new comparisons rescore every baseline consistently.

| Checkpoint | Public diagnostics | Release decision |
| --- | ---: | --- |
| Production base | 11/24 | Reference |
| Original trained parent | 14/24 | Reference |
| Previous 0.12 candidate | 15/24 | Failed review |
| Recovery stage 1 | 15/24 | Failed regressions |
| Recovery stage 2 | 19/24 | Failed regressions |
| Recovery stage 3 | 21/24 | Failed document extraction |
| Transfer repair | 20/24 | New retention regressions |
| Stability repair | 24/24 | Manual review and transfer limitations remain |
| Preference repair | 20/24 | New regressions; inactive |
| Same-lineage parameter mean | 24/24 | Manual permission/approval failures; inactive |

The first three recovery stages used 600 CPU updates: 36,258 input tokens, 9,858
assistant-target tokens, and 1,235.47 seconds of measured training-loop time.
Later stages use explicit training-only replay and lower learning rates. Reports
record actual tokens, runtime, seed, learning rate, replay steps, row IDs, losses,
model hashes, and unchanged-parent checks. No GPU was available; GPU utilization
is unmeasured rather than fabricated.

The stability candidate scored 16/18 on independently worded transfer probes,
compared with 9/18 for the previous trained candidate. New-curriculum held-out
target loss fell from 0.9715 to 0.1052 across 56 examples. Previous-domain held-out
target loss rose from 3.2076 to 3.4212 across 19 examples. Transfer answers included
a science-fact error; raw review found permission and approval-state wording that
keyword checks accepted incorrectly. Automated 24/24 did not authorize activation.

Reviewed preference optimization is a subsequent experiment. Chosen responses
preserve authorization, task state, and relevance; rejected responses grant false
authority, lose pending approval, or substitute unrelated filler. A second transfer
suite was written before preference training began. The preference candidate
scored 20/24 and remains inactive. Same-lineage parameter averaging is a subsequent
stability experiment with zero additional gradient steps; it preserves the rank,
tensor keys and shapes, base identity, tokenizer, and all source checkpoint files.
It scored 24/24 under the legacy prompt, but manual review again rejected its
permission and approval answers. Under the shared application policy it scored
23/24: the untrusted-instruction response improved while the summary omitted
missing owner approval. These protocols are recorded separately; policy changes
are not attributed to weight training. Matched-policy baselines and fresh transfer
measurements are being collected. No model release is approved yet.

## Evidence and reproduction

The [evidence directory](benchmarks/recovery-v1/) includes frozen source data,
training/validation/test partitions, replay snapshots, actual training reports,
raw answers, corrected comparisons, and the fresh-suite fingerprint. Replay comes
only from historical training partitions. Previous validation and test rows never
become replay. The archived stability builder records the exact source revision
used for that dataset; the current builder uses portable paths.

Use the frozen datasets for reproduction. Builder changes can alter provenance
fingerprints even when teaching examples remain equivalent. The three original
recovery stages used 200 steps each, learning rate 0.00005, replay fraction 0.25,
and schedule offsets 0, 200, and 400. Transfer repair used 200 steps at 0.00005
with replay fraction 0.5. Stability repair used 200 steps at 0.00002 with replay
fraction 0.5. Preference repair used 64 DPO steps at 0.00001 with replay fraction
0.5. All use seed 42, a 256-token training limit, and CPU execution. Optimizer
state resets explicitly between saved stages.

```text
zenith continue-training --parent VERIFIED_PARENT --dataset FROZEN_DATASET --output NEW_CHECKPOINT --steps 200 --learning-rate 0.00002 --replay-fraction 0.5 --device cpu
zenith expansion-eval --parent NEW_CHECKPOINT --output NEW_DIAGNOSTICS.json
```

These are authored development curricula with related template families, not a
comprehensive expert corpus. Public diagnostics guided error analysis and
candidate selection. Fresh probes provide additional evidence but remain small;
base-model pretraining contamination of common facts cannot be ruled out. Loss
values are means of per-example assistant-target negative log likelihood.
Latency varies with answer length and CPU contention; no speed parity with hosted
assistants is claimed.

[Promotion controls](model-promotion.md) reject missing cases, altered scores,
changed checkpoints, mismatched protocols, and regressions hidden by averages.
Local activation requires explicit approval, real loading and inference, a backup
of the prior profile, and a runtime checkpoint receipt. Existing memory, login,
and execution controls remain preserved.
