# Continued training of the existing Zenith checkpoint

This work extends the existing Zenith adapter and application. It does not create a foundation model, reset the original adapter, change vocabulary IDs, or replace the network architecture. Candidate weights remain local and unpromoted; the source release adds the reviewed continuation and execution controls.

## What actually exists

The GitHub source tree contains the application, original educational Tiny architecture, and training code. It does not include a standalone trained Tiny foundation checkpoint. Inspection found a previously trained Zenith LoRA artifact in the execution workspace, backed by the already cached, pinned `Qwen/Qwen2.5-0.5B-Instruct` checkpoint. That artifact is the parent used here. Its earlier report explicitly retained the production base because of regressions; it was not assumed to be a production-approved model.

The verified architecture is `Qwen2ForCausalLM`: 24 decoder layers, hidden size 896, 494,032,768 base parameters, and the parent's existing rank-8 LoRA with 4,399,104 adapter parameters. The architecture supports a 32,768-token context. The unchanged tokenizer has 151,665 entries; the embedding vocabulary is larger, as recorded in the inspection report. Actual training used sequences of at most 256 tokens on CPU. No long-context training gain is claimed.

Original base revision: `7ae557604adf67be50417f59c2c2f167def9a775`. Original trained adapter file: 17,640,136 bytes. All parent file hashes were checked before and after training. A real inference check returned `4` for the arithmetic prompt. [Inspection evidence](benchmarks/continuation-v1/parent-inspection.json) records architecture, versions, tokenizer fingerprint, checkpoint sizes, hashes, and the prior training history.

## Actual experiment and decision

The accepted experiment continued the existing adapter through two versioned candidates: 48 optimizer steps, then 32 steps from that newly trained candidate with the deterministic curriculum schedule continued at offset 48. Optimizer state was reset explicitly between phases; this is weight continuation rather than a claim of an exact optimizer-state resume.

| Measurement | Result |
| --- | --- |
| Accepted optimizer steps | 80 |
| Input tokens processed, including repeated context | 5,567 |
| Assistant target tokens processed | 2,314 |
| Historical replay steps | 20 |
| Accepted training time | 126.331 seconds on CPU |
| CUDA/GPU utilization | Not applicable; no CUDA device available |
| Validation target loss | 3.683 → 3.298 |
| Held-out target loss | 3.559 → 3.208 |
| Production diagnostic answers | 11 / 24 |
| Parent diagnostic answers | 14 / 24 |
| Candidate diagnostic answers | 15 / 24 |
| Promotion gate | Failed: instruction-following and retrieval-grounding regressions |
| Production changes | None |

The answer suite uses small authored tasks and transparent rule/structure scorers. It is not a standardized expert benchmark or a claim of broad intelligence improvement. Algebra requires a completed solution, and structured JSON must parse without Markdown fences. The initial scorer incorrectly accepted an incomplete algebra response and fenced JSON; version 2 rescored the saved outputs, preserving the originals for review. The final decision uses version 2.

The candidate repeated `orbit` instead of following the single-word instruction and fabricated an annual budget absent from the supplied document. Those failures prevent promotion despite lower loss. [Per-task answers and slices](benchmarks/continuation-v1/candidate-benchmark.json), [comparison](benchmarks/continuation-v1/comparison.json), and [experiment metadata](benchmarks/continuation-v1/experiment.json) are included.

A reproduction using the final training implementation produced bitwise-identical values for all 336 adapter tensors. [Reproduction evidence](benchmarks/continuation-v1/reproducibility.json) distinguishes that verification run from the accepted training metrics above. [Weight deltas](benchmarks/continuation-v1/weight-update.json) confirm that learned adapter values changed while keys and shapes stayed fixed.

An initial run was interrupted after discovering that historical replay had been split into evaluation partitions. Its weights were excluded. The corrected dataset places all historical training replay exclusively in training. No candidate descends from the interrupted run.

## Curriculum and data isolation

The frozen [dataset](benchmarks/continuation-v1/dataset/manifest.json) contains an authored Apache-2.0 technical primer plus the verified historical training partition. It is a small teaching corpus, not a comprehensive resource library or independent expert certification. Source identifiers, rights declarations, revisions, hashes, document groups, and explicit training approval are retained.

The primer covers AI, programming, infrastructure, mathematics/science, reasoning, structured calls, retrieval/memory, and planning. Cybersecurity lessons use the requested White, Blue, Green, Gray, Red, and Black Hat classifications for authorized assessment, defense, fundamentals, disclosure, emulation/detection, and malicious-technique investigation. The curriculum contains no intrusion tooling, credential-theft procedures, ransomware deployment, destructive attacks, or retaliation workflows.

New source records are grouped and split before replay is appended to training. The resulting partitions contain 100 training, 19 validation, and 19 held-out test examples; training includes 40 historical replay records. Previously trained replay prompts are prohibited in validation and test. All new training records were covered by the accepted schedule. No held-out targets were used for gradient updates. Diagnostic generation and held-out loss were evaluated after the fixed training schedule. Do not tune future candidates repeatedly against this now-public test version; create a new independent final evaluation for future selection.

## Reproduce a continuation

Use an activated source installation with training dependencies and the original local parent adapter available. The base checkpoint must already be cached at its recorded revision; the loader uses local files only, safetensors, and disabled remote custom code.

```bash
python -m pip install -e ".[train,test]"
zenith checkpoint --parent /absolute/path/to/existing-zenith-adapter --output artifacts/parent-inspection.json
python -m scripts.prepare_expansion_curriculum --output artifacts/curriculum-next --replay docs/benchmarks/v0.6/frozen-pilot-dataset/train.jsonl
zenith continue-training --parent /absolute/path/to/existing-zenith-adapter --dataset artifacts/curriculum-next --output artifacts/candidate-next --steps 80 --device auto
```

Create the `artifacts` parent directory before an inspection output if necessary; the inspection command creates parent directories and refuses to replace an existing report. Every candidate output must be a new directory outside the original checkpoint. The loader rejects missing trained artifacts, untrained zero-B adapters, absent training evidence, inconsistent base revisions, partial base loads, and incompatible tokenizers. It loads the existing adapter with `is_trainable=True`; it never calls the new-adapter initializer.

`--device auto` selects CUDA when available, otherwise CPU. This experiment was CPU-only. GPU utilization percentage is not invented when unmeasured; future CUDA runs record peak allocated memory. PEFT was selected because the available CPU environment has an 8 GiB memory limit. Full-parameter training was not performed.

Training modes:

| Objective | Required data and behavior |
| --- | --- |
| `--objective sft` | Reviewed instruction records; loss only on the final assistant target |
| `--objective cpt` | Reviewed `text` with rights/provenance; causal loss across domain text |
| `--objective dpo` | Reviewed `chosen` and `rejected` responses plus `preference_validated: true`; reference log probabilities fixed before optimization |

CPT and DPO are implemented objective paths, not experiments claimed in this report. Coding, mathematics, cybersecurity, retrieval, structured calls, and planning use ordinary SFT records in the accepted experiment. Structured output is training data; it does not grant permission to execute a tool.

For a full review cycle:

```text
zenith continuation-campaign --parent ORIGINAL_ADAPTER --dataset VERSIONED_DATASET --output NEW_RUN --steps 80
```

The campaign saves inspection, parent/production baselines, a separate candidate, candidate evaluation, and a review report, and returns a failing exit status when numeric gates fail. It never edits the active profile or deploys weights. Legacy scratch-model training commands remain separate educational workflows; they are not used to expand the trained Zenith parent.

## Merge/export and rollback

```text
zenith export-checkpoint --parent CANDIDATE_ADAPTER --output NEW_LOCAL_EXPORT
```

Export merges the existing adapter with its original base using safe merge, compares logits, saves safetensors and the unchanged tokenizer, reloads the exported model, and verifies logits again. It preserves the source checkpoint and refuses an existing output directory. The local compatibility export in this experiment is 1,992,067,317 bytes before its report. Maximum merge logit difference was approximately 0.0000229, within the recorded float32 tolerance. [Export evidence](benchmarks/continuation-v1/export-report.json) contains file hashes and sizes.

An export checks format compatibility; it is not deployment approval. This candidate failed the quality gate. Its adapter, full compatibility export, and reproduction artifacts remain local and inactive. No weights are committed, uploaded, or published. The current production profile, original base cache, and parent adapter remain unchanged. A future approved deployment must keep the previous adapter and settings, validate the chosen model/tokenizer, and permit rollback by restoring the prior `ZENITH_ADAPTER` setting and restarting Zenith. Approval must precede publishing or production changes.
