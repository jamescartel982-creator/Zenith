# Approved, opt-in Hermes chat compatibility

The owner approved this separate compatibility build after the real native
Hermes test rejected Zenith's 32K architectural limit under its 64K custom-provider
floor. Original Hermes at `d05095663342556788cf2a198bfa7844cc7968ab` and its MIT
license stay intact. The builder exports its complete tracked source to a new
directory, preserves all upstream notices and applies narrowly scoped context, capability and served-runtime metadata changes
in that copy only. It never replaces a model, tokenizer, adapter, checkpoint or
native profile. Existing destinations, dirty sources and mismatched audited
file hashes are refused.

```bash
python integrations/hermes_compat/build.py \
  --source /path/to/pinned/hermes-agent \
  --output /path/to/new/hermes-zenith-chat
```

Install the copy's **unchanged frozen** dependencies in a separate environment
with Python **3.14.8**, uv **0.12.23**, and the `messaging` extra. Zenith continues
using its own Python 3.12 environment; dependency manifests are not combined.
Initialize a separate Hermes home with authenticated loopback API, `custom`
provider, model `zenith`, its dedicated local inference URL/key handle, an exact
context window that inference actually serves, `platform_toolsets.api_server:
[]`, no external model fallback, `agent.reasoning_effort: false` and bounded turns.
Use an API agent alias distinct from the raw model ID (for example
`gateway.api_server.model_name: hermes-agent` while `model.default: zenith`).
Zenith accepts explicit `reasoning_effort: none`; unsupported active effort
settings are rejected rather than silently ignored. Do not put its standalone home
under a `profiles/` directory: native multiplexing treats that as a secondary
profile and may intentionally suppress its separate listener.

Start the native runtime from the compatibility directory with:

```bash
HERMES_HOME=/private/hermes-zenith-chat \
ZENITH_HERMES_CHAT_ONLY=1 ZENITH_HERMES_PROFILE_ID=zenith-hermes-chat \
/path/to/separate/hermes-python -m gateway.run
```

These are non-secret policy flags. Keep the generated API and inference keys in
owner-only native secret files/environment handles, outside prompts and logs.
For a new bridge profile, explicitly supply `--hermes-compat-manifest-file
/path/to/new/hermes-zenith-chat/zenith-compat-build.json` and the matching
`--hermes-profile-id zenith-hermes-chat`. Defaults remain off.

The native exception requires `custom` + `zenith`, API-server platform, loopback
`/v1`, exactly empty selected and constructed tool lists, and a real configured
4K–32K window. All other routes retain the original 64K rule. The native API
advertises a policy/build digest only when its configured profile is eligible.
The compatibility copy also records the actual post-turn agent model/provider
in committed usage metadata; it never copies requested labels into attribution.
The audited Runs path did not forward the session model-lock option, so the
bridge does not pretend that unsupported request field enforces a lock.
The bridge independently hashes the selected compatibility files, compares the
advertised profile/build/context to actual authenticated inference readiness,
then requires the original owner/MFA exact message grant. Tampered or mismatched
builds fail closed. This is source integrity on a trusted host, not remote
attestation or protection from a compromised host administrator.

This enables a restricted native chat surface. It does **not** certify full
Hermes tools, long-context performance, native feature parity or model quality.
The actual native chat test completed in 9.777 seconds with answer `4`, 620 input
and 2 output tokens, and verified served model `zenith` / provider `custom`. See
`docs/four-system/implementation-v0.4/local-hermes-chat-acceptance.json`. Full
four-runtime owner/MFA acceptance and retained native regressions still apply.

Rollback: stop only this compatibility process and remove its bridge opt-in;
retain native receipts/state and restart the original unmodified Hermes runtime.
No original checkpoint or memory migration is involved.
