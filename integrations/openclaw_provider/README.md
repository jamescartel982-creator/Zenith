# Zenith local provider compatibility

This optional OpenClaw provider plugin uses the public `registerProvider` and
`buildReplayPolicy` / `wrapStreamFn` SDK interfaces at upstream commit
`2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`. It does not patch OpenClaw,
change Zenith weights, switch models, execute tools, or rewrite user input.

The original generic OpenAI-completions policy retains temporal runtime-context
carriers to support exact-entry prefix caches. Zenith's local service has no such
cache or prefix-bound reasoning. Empty interrupted-input snapshots distracted the
small preserved model: it answered `none in the latest retained-input page`.
This provider keeps the SDK's normal replay sanitation, but selects
`appendOnlyRuntimeContext: false` for the explicitly configured local Zenith
endpoint. OpenClaw then uses its native current-turn context projection rather
than retaining empty snapshots after the user request. Nonempty current runtime
facts remain handled by native OpenClaw code. A native stream wrapper moves only
producer-tagged trailing runtime carriers before the active user request. It
preserves every message, text, role, option and cancellation signal; it never
infers provenance from text markers, crosses tool/operator turns, or rewrites
the native transcript. The wrapper leaves tool-enabled contexts unchanged.

Load this directory through an operator-owned OpenClaw configuration:

```json
{
  "plugins": {
    "enabled": true,
    "allow": ["zenith-local-context"],
    "load": {"paths": ["/absolute/path/to/Zenith/integrations/openclaw_provider"]},
    "entries": {"zenith-local-context": {"enabled": true}}
  }
}
```

Archive the existing private configuration before changing it. Retain any other
explicitly approved plugins in the allowlist; do not overwrite their settings.
This plugin deliberately refuses remote URLs, reasoning models, non-Zenith model
IDs and unsupported transports. Dedicated model credentials remain in the
existing environment/secret files, outside prompts and this package.

Run policy tests with `node --test integrations/openclaw_provider/test-policy.mjs`.
The pinned-native CI job also exercises real Gateway/model inference and frozen
addition, multiplication and exact-instruction cases. A green unit test alone
does not establish answer quality; consult the native acceptance artifact.
The initial native trial removed the empty interrupted-input echo but failed
arithmetic by echoing temporal context instead. This failure is retained in CI
run 40606994974; the additional stream projection must pass fresh acceptance.
Broad reasoning, trading accuracy and full upstream feature parity remain
unverified. Known context-echo detection remains active.

Rollback: stop the native Gateway, restore its archived plugin configuration,
and restart it. Retain sessions, receipts, model files and the original source.
No tokenizer or checkpoint migration is needed.
