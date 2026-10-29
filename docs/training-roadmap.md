# A bounded two-week improvement plan

The repository provides runnable experiments and a first completed starter training run. Development does not continue unattended for two weeks after this session. Longer runs need your machine or CI, a compute/storage budget, selected data, and subject review. No finite collection can cover everything, and indiscriminate scraping is not a reliable training method.

| Days | Work and reviewable output |
| --- | --- |
| 1–2 | Choose target users/tasks and hardware. Freeze baseline model/revision, speed budgets, representative prompts, abstention expectations, and error costs. Keep a separate sealed final test. |
| 3–4 | Select original or permitted math, science, history, ancient mathematics, coding, cybersecurity, and financial education material. Preserve source snapshots/rights, clean duplicates and secrets, label topics/difficulty, obtain domain review. |
| 5–6 | Prepare versioned document/prompt-disjoint training and validation partitions. Inspect topic/subgroup coverage and near-duplicates. Use cited retrieval for material needing updates rather than asserting it was learned. |
| 7–8 | Run one bounded candidate experiment, then error analysis on validation slices. Compare latency, answer completeness, unsupported claims, abstention, and errors. Preserve failed candidates; change one major variable at a time. |
| 9–10 | Add noisy, ambiguous, adversarial, unfamiliar-topic, and deployment-specific subgroup cases. Fit aggregate calibration on independent validation labels if adequate data exist. Exercise owner/auth boundaries and human review. |
| 11–12 | Select a candidate without consulting the final test. Run that sealed test and independent calibration evaluation; require no unacceptable regression. Investigate false positives in automated scoring with human review. |
| 13–14 | Test Windows/Linux installs and target hardware. Review artifacts and rights, explicitly activate the selected adapter, retain the previous profile for rollback, and monitor actual user errors. |

Use `zenith campaign --output artifacts/experiment-001 --max-steps 40` for the first bounded experiment, then create a new output directory for each revision. The starter command caps local optimizer steps at 5,000; GitHub's manual workflow accepts 1–200. More steps on a tiny dataset can worsen answers. Do not promote from loss alone or repeatedly tune against a sealed test; create a fresh test version if it becomes development feedback.

The [conversation skills](skills.md) comprise 16 public profiles and 16 owner-only security profiles with explicit commands and live authorization checks. AI engineering is implemented in the codebase and documented in [development standards](engineering.md), rather than offered as a selectable subject. Profiles and source links are not automatically used for training and do not establish certification or learned expertise. Financial examples cover education and risk, not guaranteed returns or live execution. Security tools remain an owner-controlled offline workbench. Larger models need suitable RAM/VRAM and measured deployment tests.
