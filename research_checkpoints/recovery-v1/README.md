# Zenith continued-learning research snapshot

Status: **experimental; explicit owner activation with known regressions is available**.

These are actual learned adapter weights from the existing Zenith continuation
chain. The unchanged base is Qwen/Qwen2.5-0.5B-Instruct at revision
7ae557604adf67be50417f59c2c2f167def9a775. Base weights are downloaded separately.
The adapter keeps rank 8, 336 tensors, the original architecture and tokenizer.
All original checkpoints remain unchanged. The snapshot is the equal parameter
mean of three adjacent versions of the same adapter, after actual SFT and DPO;
this last averaging operation adds zero training steps or training tokens.

Legacy automated diagnostics reached 24/24, but manual permission and approval
review failed. The application-policy protocol reached 23/24 and omitted pending
owner approval. Fresh transfer was 15/20 versus 17/20 for its immediate parent and 12/20 for the
previous trained reference. Retained-domain loss worsened from 3.2076 to 3.3734.
These are known regressions. Raw measurements and matched baselines are recorded
in docs/benchmarks/recovery-v1. These small authored checks do not establish
expert competence or broad safety. This snapshot does not enable restricted tools.
The supplied research.json deliberately disallows deployment use-release.
An operator can explicitly accept the recorded regressions from the repository:

```text
zenith setup --activate-candidate
```

This creates a reversible experimental activation receipt and preserves the
failed evaluation decision. The checkpoint files themselves are unchanged.

From an installed environment with the pinned base cached, verify real loading:

```text
python -m scripts.check_research_checkpoint --bundle research_checkpoints/recovery-v1
```

The weight file is stored as ordered binary parts to respect upload limits.
Reconstruct an exact checkpoint in a **new** directory:

```text
python -m scripts.materialize_research_checkpoint --bundle research_checkpoints/recovery-v1 --output PATH_TO_NEW_CHECKPOINT
zenith checkpoint --parent PATH_TO_NEW_CHECKPOINT
```

The helper verifies every part and every reconstructed file. It never overwrites
an existing directory or changes source files. Then continue training only into
a separate new directory using the existing
continue-training command and licensed, validated data. Never overwrite this
snapshot. Embedded historical paths describe the original experiment; they do not
need to exist for loading this adapter. No API key or credential is included.

Zenith-authored code/data and adapter: Apache-2.0; see LICENSE. Original upstream
identifiers and PEFT metadata are preserved. Qwen2.5-0.5B-Instruct is Apache-2.0;
its upstream notices and terms also apply. See the project model card for results
and limitations. The GitHub source manifest and research.json verify byte integrity,
not publisher authenticity against a hostile filesystem owner.
