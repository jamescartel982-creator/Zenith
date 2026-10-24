# Zenith model card

Current recovery status: **experimental; explicit owner activation is available with known regressions**.

The existing rank-8 adapter continues the original pinned Qwen2 architecture and
tokenizer. The stability-repair candidate reached 24/24 on the public development
diagnostics and 16/18 on the first transfer probes. Raw review found misleading
permission and approval-state wording, and retained-domain loss increased from
3.2076 to 3.4212. These results do not establish readiness for production.

A 64-step preference repair scored 20/24 and introduced further regressions.
Same-lineage parameter averaging scored 24/24 under the legacy prompt but failed
manual permission/approval review. With the shared application policy it scored
23/24, still omitting owner approval in a summary. These different inference
protocols are reported separately. Averaging performs no new gradient updates.
On matched application-policy runs, the parameter mean scored 15/20 fresh tasks
versus 17/20 for its immediate parent and 12/20 for the previous trained reference.
It confused forensic hashing with password hashing. Retained-domain loss was
3.3734, above the previous reference's 3.2076. Promotion remains rejected.
All original source checkpoints remain preserved. An owner can explicitly select
the combined candidate with `zenith setup --activate-candidate`; the activation
receipt retains the failed gate and rollback path.

The small authored Apache-2.0 curricula were guided by public diagnostic failures.
Exact diagnostic prompts and old held-out rows are excluded from gradient updates,
but the development score is not an independent estimate of expert competence.
See [recovery evidence](model-recovery.md), [promotion controls](model-promotion.md),
and [execution controls](execution-controls.md). Model activation never enables
restricted execution tools or bypasses MFA and target-scope checks.

The [research snapshot](../research_checkpoints/recovery-v1/) contains the actual
experimental adapter and tokenizer. It is rejected by the
approved-release activation workflow; a separate explicit experimental override
is available. Base weights remain a separate pinned download.

The workspace profile was explicitly activated under the owner's regression
exception in 0.14. This is an operator deployment decision, not a passing quality
evaluation. [Activation and rollback evidence](benchmarks/activation-v014/) records
real loading and inference. Other installations select it with the setup command.

## Historical 0.12 pilot

Status: **experimental, local, not promoted or published**.

This is a continuation of Zenith's existing trained LoRA checkpoint on its unchanged Qwen2 base. It is not a new foundation model. Original architecture, tokenizer, upstream identifiers, licenses, and parent checkpoint files are preserved. The application identity remains Zenith in the existing GitHub repository.

The accepted CPU pilot used a small authored technical curriculum and historical training replay. It lowered held-out target loss, but failed deployment gates because instruction following and retrieval grounding regressed. The observed aggregate diagnostic change is insufficient to claim broad capability improvement or professional cybersecurity competence. It is not a replacement for the existing production profile.

See the [training report and limitations](continued-training.md), [frozen experiment](benchmarks/continuation-v1/experiment.json), [raw answers](benchmarks/continuation-v1/candidate-benchmark.json), and [execution controls](execution-controls.md). The six hacker classifications organize defensive and authorized research education. Neither a classification nor an admin code disables or enables information in neural weights; tool permissions are enforced separately.

Future work requires representative licensed data, stronger independent evaluation, deliberate preference-pair validation, appropriate compute, and review of regressions before any approval to deploy. No hidden autonomous training, automatic promotion, or unapproved publication is enabled.
