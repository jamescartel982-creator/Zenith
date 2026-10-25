# Platform architecture references

Zenith remains licensed under its existing Apache-2.0 [LICENSE](LICENSE).
The platform design was informed by a source-level review of
[OpenClaw](https://github.com/openclaw/openclaw/tree/2f5727b9c61c2ba9dccc3c880d9115f02cb8652f),
copyright 2026 OpenClaw Foundation, MIT licensed. Immutable path/line references
and scoped notices are recorded in [the audit](docs/openclaw-audit/reports/OPENCLAW_REVERSE_ENGINEERING.md).

This pilot is a Python-native implementation using Zenith's existing dependencies.
It does not vendor OpenClaw runtime code, plugins, skills, logos, artwork, npm
packages or model artifacts. No third-party license or ownership identifier has
been removed from the existing repository or models. Architectural inspiration
does not establish runtime/plugin/wire compatibility.

Before adapting specific upstream code/assets in a later stage, retain its
copyright/license, exact commit/path/hash and applicable scoped notices. OpenClaw's
root MIT license does not replace separate licenses for its assets, dependencies,
native components or external models/services. Existing model-pack notices remain
in `vendor/model-packs/NOTICE.md`; existing dependency and model terms still apply.
