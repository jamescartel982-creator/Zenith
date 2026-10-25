# Bounded reasoning (Phase 3)

Zenith 0.16 adds an opt-in inference harness around the existing trained model and provider registry. This is application logic, not a new model, learned capability, adapter, tokenizer change or training run. Existing installation commands and saved profiles stay unchanged. The registry/orchestration update is already merged in PR #17; Phase 3 is a separate feature for review.

## Use

```bash
zenith reason "Compare two approaches to this problem." --effort deep
zenith reason "What is 2 plus 2? Return only the digit." --effort standard --expression "2+2"
zenith reason "Explain binary search." --effort fast --max-calls 1 --max-output-tokens 96
```

From the installed checkout, use its `run.sh reason ...` / `run.ps1 reason ...` launcher, or `python -m agent reason ...` with the installed interpreter. `--timeout` bounds the cooperative overall deadline. `--max-calls` can reduce the default budget; it never expands it. Native cached inference is the default. External routing requires the existing exact account-visible model configuration and an explicit `--allow-external`; offline settings continue to disable it. No keys are bundled or requested by this command.

For ongoing browser/terminal chat, explicitly select `AI_PROVIDER=reasoning` and set `ZENITH_REASONING_EFFORT=fast|standard|deep|research`. The existing `ZENITH_ORCHESTRATION_MODE` selects individual native/fast/coding/research/local-only routes; nested collaborative/security modes are rejected. The separate response-length Fast/Thorough controls still apply. Ordinary chat has no code-execution session or grant. Imported SQLite excerpts are passed as untrusted evidence and cleared from the provider when the request ends; conversation/account boundaries are preserved.

| Effort | Maximum default model calls | Behavior |
| --- | --- | --- |
| Fast | 1 | One candidate and any explicitly declared deterministic checks. |
| Standard | 4 | Candidate, separate review, optional correction and re-review. |
| Deep | 7 | Short proposed checklist, two independent candidates and reviews, at most one correction/re-review within the remaining budget. |
| Research | 9 | Proposed checklist, two or three candidates depending on task size, reviews and one correction/recheck. Uses existing supplied/retrieved sources; multi-query web research remains Phase 7. |

Retries and fallback attempts count against the same total as successful calls. Every stage shares the original deadline and estimated provider-cost cap. CPU/GPU model loading and blocking I/O remain cooperatively cancellable; no strict preemptible GPU/kernel deadline is claimed. Native streaming remains available in the old provider; this optional reasoning path buffers completed/reviewed answers and reports its whole latency, not model TTFT.

Plans are short, schema-checked task checklists, explicitly non-executable and untrusted. Invalid model checklists fall back to a labeled template. Independent candidates receive fresh answer contexts; reviews are separate calls. With only native configured, these calls use the same original checkpoint, not independently trained brains. No hidden proprietary reasoning is requested or exposed.

## Verification and uncertainty

`--expression` declares a bounded arithmetic constraint. Exact decimal/fraction arithmetic reuses `agent.tools.calculate`; numeric candidates are compared as fractions. This is not a general mathematical proof system. Declared failed/rejected checks cannot be overridden by a positive model review. One correction is allowed; if checks still fail, the harness abstains. A corrected answer without a valid fresh review remains unverified.

Citation checks verify that supplied URLs or `[S1]` identifiers refer to available source excerpts. Unknown references fail. URL/identifier membership **does not prove factual support, credibility or completeness**; claim support remains explicitly unverified. Review JSON is fallible model feedback. Missing/malformed/contradictory reviews never become calibrated confidence or a successful model-promotion gate. Responses preserve producer identity, stage/call counts, usage when available, checks, abstention and uncertainty in their saved deliberation trace.

The authored diagnostic suite is `agent/evaluation/reasoning-v1.json`. [Raw native results](native-diagnostics.json) record suite/configuration hashes, exact model/revision/adapter, responses, checks, calls and latency. On the existing CPU adapter, baseline and Standard reasoning both scored **2/3** exact answers. The JSON case differed by whitespace from the explicitly required exact output. Standard reasoning took roughly 6.4, 14.0 and 6.0 seconds for the three probes; structured model review remained unverified. This is measured overhead without a demonstrated quality gain. No GSM8K, HumanEval+, SWE-bench, frontier parity, GPU, speedup or calibrated-confidence claim is made. Better model review requires further validated work rather than relabeling invalid review output.

## Authorized numeric code verification

The new `verify-python` capability is disabled by default. The existing `/api/admin/execution/grant` and `/api/admin/execution/run` routes enforce live owner identity, MFA, a short-lived explicit `{"kind":"offline"}` grant, audit, revocation and emergency stop. Granting the capability does not activate a model-selected shell or execute an unreviewed plan.

Its arguments are a reviewed `source`, `entrypoint` and one to 16 cases such as `{"args":[3],"expected":6}`. Supported programs consist of exactly one small numeric function with numeric/boolean parameters and returns, ordinary bounded arithmetic, assignments, comparisons, conditions, and `abs`/`min`/`max`. Imports, attributes, filesystem/network primitives, shell, loops, user recursion, decorators, annotations, arbitrary builtins and builtin shadowing are rejected. Wrong answers are failed cases; unsupported syntax is explicitly rejected.

The host executes a fixed trusted worker with isolated Python flags, a temporary working directory, no inherited application credentials, a five-second subprocess timeout, bounded input/output, 512 AST nodes and 1000 interpretation steps. Submitted source is interpreted through an AST allowlist; it is never passed to `eval`, `exec` or a shell. **This is a deliberately restricted language interpreter, not a general Python or OS-level sandbox.** General code execution and repository agents require the later Phase 4 isolation work. Process privilege itself is not claimed to be constrained by an OS container.

Trusted application integrations can supply an explicit `code_check` and live `ExecutionControls` session to `ReasoningEngine.run`. Authorization is checked before any model call, for each actual code test, and again before releasing results. Secrets stay outside messages. Public chat/CLI never constructs that session from prompt text. The model cannot authorize itself.

## Validation and rollback

The original 243-test baseline and trained artifact hashes are preserved. New tests cover candidate selection, correction/review budgets, cancellation, arithmetic, evidence identifiers, real chat/SQLite integration, actual subprocess execution/rejection and real owner/MFA grant/stop enforcement. Native installed Windows/Linux CI runs the frozen real-model diagnostics. See the PR for final test results and CI status.

No database migration, profile edit, new memory database, training, checkpoint merge, weight update or promotion occurs. Restore the prior `AI_PROVIDER` and restart to disable reasoning; application commits can be reverted without changing model/data artifacts. Existing code-verification grants remain subject to expiry/revocation and default-deny checks. Phases 4–15 remain planned.
