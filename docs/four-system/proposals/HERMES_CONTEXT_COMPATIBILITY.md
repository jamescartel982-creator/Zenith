# Decision needed: Hermes native context compatibility

Actual test, October 27, 2026: the pinned, unmodified Hermes API accepted a
run, then failed agent construction in `agent/agent_init.py` at
`_enforce_minimum_context`. Its custom-provider route requires **64,000 tokens**.
The unchanged Zenith model has **32,768 architectural positions**; its current
inference service serves **8,192 tokens**. Increasing the advertised context to
64K would misrepresent the model and does not solve this incompatibility.

The native API itself is authenticated and durable. Its initial profile has no
enabled toolsets. This is transport availability, not working agent inference.
The bridge now refuses this combination before submitting work and reports
`native_context_window_below_64000`. No upstream files or model files were patched.

## Proposed, unapplied compatibility change

Keep the audited upstream tree immutable. Build a separate, explicitly versioned
Hermes compatibility checkout with an opt-in **chat-only** small-context policy:

1. `agent/agent_init.py::_enforce_minimum_context`: permit an explicitly configured
   window only for provider `custom`, model `zenith`, local inference endpoint,
   platform `api_server`, an exactly empty toolset list and no constructed tools.
   Require a real configured window of 4,000–32,768 tokens; never expand it or
   pretend to provide Hermes' full agent/tool capability at that window. Preserve
   the existing default 64K floor for every other route.
2. Native API capability response: advertise the effective small-context policy,
   profile identity, supported execution surface and compatibility build digest
   so Zenith's bridge can verify it rather than trusting a prompt or URL.
3. Zenith's additive Hermes adapter: admit the smaller context only when an
   operator explicitly enables this mode and the native capability response,
   local build digest and actual inference readiness agree. Otherwise refuse it.
4. Add guard regression tests for opt-out, non-local endpoint, another model,
   tool activation, wrong platform, mismatched context and normal 64K behavior.
   Then run a real native agent turn, original owner/MFA acceptance, cancellation,
   restart tests and the relevant untouched upstream tests before activation.

This changes upstream **behavior** only in a separate compatibility build and
therefore needs the owner's specific approval under the preservation requirement.
It is not currently applied, activated, tested as a native fork or described as
full Hermes parity. The original source, native state and model remain intact.

Alternative: keep strict upstream immutability. Hermes remains available as an
independent API, but its current custom-provider agent cannot run this unchanged
Zenith model. A different foundation model is outside the approved preservation
objective and is not proposed here.

Rollback: disable the opt-in mode, stop only the compatibility runtime and retain
its execution receipts; restart the original pinned Hermes environment/profile.
No original model or native memory migration is involved.
