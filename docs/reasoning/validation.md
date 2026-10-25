# Phase 3 validation record

Baseline: merged Phase 1/2 commit `e6963d9c6f45c196ae2e301819ae1ae093b35c41`, 243 tests with one local skip, all seven GitHub checks and separate diagnostic watch green before implementation.

Full local Phase 3 suite: **262 tests, one skip, no failures**, **31.416 seconds** on Linux/Python 3.12. Nineteen new tests cover shared retry/call budgets and deadlines, plan authority, separate candidates and review/correction, exact math, unknown sources, actual chat/SQLite provenance, actual numeric-subset subprocess execution/rejection, secret-free child environment and the existing live owner/MFA/grant/stop workflow. The original 243 tests remain included.

Real unchanged-checkpoint diagnostics: [native-diagnostics.json](native-diagnostics.json), frozen suite `agent/evaluation/reasoning-v1.json`, configuration and suite SHA-256 recorded. Both baseline and Standard reasoning scored 2/3 exact outputs. Arithmetic responses `4` and `0.75` matched expectations; the JSON response included whitespace and failed the explicit exact-format case. Reasoning used 2, 4 and 2 calls, took 6426.649, 14001.910 and 5965.122 ms, and retained unverified critique status. These measurements show no quality or speed improvement. They are authored harness diagnostics, not GSM8K/HumanEval+/SWE-bench or a trained-model promotion test.

The actual CLI fast reasoning path with a declared `2+2` constraint was also run against the original adapter. Checkpoint inventory and saved profile remain unchanged. No original architecture, tokenizer, weights, adapter, corpus, application data or deployment receipt was replaced or retrained. Source release verification covers all 385 inventoried files. Native installed Windows/Linux CI runs both the original orchestration smoke and the new real reasoning diagnostics; check the PR for its final results.

No external provider credentials were used. No proprietary API inference, GPU utilization/VRAM, calibrated confidence, general-Python sandbox or frontier-model capability claim is made. Code execution is limited to the documented numeric subset, default-disabled behind existing owner/MFA grants. Later phases remain planned.

A regular 0.16.0 wheel was installed into a separate environment and run with Python isolated mode outside the checkout. Installed integrity passed (122 files), and actual fast native reasoning returned `4` with a passed declared `2+2` check.
