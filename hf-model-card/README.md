---
license: apache-2.0
language:
  - en
pipeline_tag: text-generation
base_model: Qwen/Qwen2.5-0.5B-Instruct
library_name: peft
---

# Zenith LoRA — model card template

**Template only: replace all run details before publishing an actual adapter.** This metadata matches the default Apache-2.0 Qwen base. If changing the base, verify its license and update this card.

- Base checkpoint and revision: copy from `training_report.json`.
- Training data: describe provenance, consent, dataset size, domains, languages, and the train/evaluation split. Exclude private conversations and secrets from the public artifact.
- Method: PEFT LoRA with final-assistant-only cross-entropy, rank 8, alpha 16; document any changes.
- Evaluation: report held-out loss before/after and task-specific checks actually run. Small smoke checks do not establish general capability.
- Runtime: load the matching base model plus this adapter with PEFT or Zenith's `ZENITH_ADAPTER` setting.
- Limitations: outputs can be incorrect, biased, or inappropriate; small datasets can overfit and reduce general performance.
- Intended use: personal assistant experiments and reviewed domain adaptation.

Publish only files you have rights to distribute. An adapter needs its base model and is not a new foundation model trained from scratch.
