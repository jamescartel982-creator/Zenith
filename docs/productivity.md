# Validated skills, CSV analysis and account preferences

This extension preserves the configured model, adapters, tokenizer, native runtime
bridges and existing conversations. It adds deterministic data summaries, explicit
account preferences and a searchable instruction library. It does not train weights.

## What is installed

The bundled library contains **32 curated instruction profiles**, including five
new workflows: `csv-quality`, `decimal-statistics`, `analysis-review`,
`evidence-check` and `adaptive-explanation`. Existing profiles and resource
references are preserved. Profiles guide a model; they are not executable tools,
professional certifications or independently measured learned capabilities.

The separate imported library supports **100,000 profiles**. It starts empty.
The load test temporarily imports synthetic profiles, verifies indexing and
authorization filters, then removes its temporary database and input. Those
fixtures are not installed as production skills. Acquiring, licensing, reviewing
and validating 100,000 useful profiles remains separate work.

The optional [generated recipe library](generated-recipes.md) is a distinct,
explicit installation of 100,000 labeled grammar combinations. It shares this
catalog's capacity and authorization controls; it is not the synthetic load-test
fixture or a claim of 100,000 individually validated skills.

## Analyze CSV without asking a language model to calculate

In the web workspace, sign in and choose **Analyze CSV**. Paste a UTF-8 CSV,
select its delimiter and run the summary. The CLI reads a regular local file:

```bash
zenith analyze measurements.csv
zenith analyze measurements.csv --delimiter semicolon
```

With an existing source checkout, `python -m agent analyze measurements.csv` also
works through the normal launcher's environment. These calculations call no
model, fetch no URLs and execute no formulas. The server does not save the
dataset or put it in chat history. The browser clears its analysis input and
results on account changes. Only paste data appropriate for the server you use;
the server receives the input even though it does not retain it.

Limits are 256 KiB, 10,000 data records, 64 columns, 4,096 characters per cell and
100 characters per column name. Column names must be unique after trimming and
case folding; malformed records fail instead of disappearing silently.

Each column reports present/missing values, numeric and excluded values, and,
where applicable, sum, minimum, maximum, median and mean. Empty/whitespace fields
are missing; `NA`, `null` and `NaN` are text. Numbers accept signed decimal syntax
with up to 30 integer and 30 fractional digits and an optional two-digit exponent;
magnitude must be at most `1e30` and scale at most 30 decimal places. Currency
symbols, grouped numbers, dates and out-of-bounds numbers are text. Numeric
summaries cover only accepted numeric cells, and count the excluded values.

Decimal sums and medians are exact within these bounds, including `0.1 + 0.2 =
0.3`. Means round to 28 significant digits. Duplicate counts compare parsed field
values, including whitespace, and do not delete rows. Formula-like fields remain
data. This feature makes no causal, predictive or investment inference.

## Save explicit response preferences

Sign in, open account settings and expand response preferences. Save or clear
reply length, tone, explanation detail and preferred language. Values come from
fixed enumerations; arbitrary instructions and permission changes are rejected.
The server derives the account from the authenticated session. No personality or
sensitive traits are inferred. An explicit reply style in the current request
takes precedence over a saved default.

Preferences use the existing account database. Clearing preferences affects
future requests; it does not erase prior conversation history. A model may still
fail to follow a preference. The preserved-model smoke test verified one French
greeting, not universal language accuracy or general error reduction.

Authenticated API routes:

| Method and path | Purpose |
| --- | --- |
| `GET /api/preferences` | Read the current account's values and allowed options |
| `PUT /api/preferences` | Merge `{"values":{"language":"fr","tone":"friendly"}}` |
| `DELETE /api/preferences` | Clear the current account's preferences |
| `POST /api/analysis/csv` | Analyze `{"csv_text":"value\n0.1\n0.2\n","delimiter":","}` |

Existing authentication, request-body limits, host/origin protections and server
deployment requirements apply. Two concurrent CSV calculations are allowed;
additional concurrent analyses receive HTTP 429 and a retry hint.

## Import reviewed instruction packs

Only a trusted local operator can import a pack. There is no HTTP import,
automatic download or code loader. Review the provenance, rights and every
instruction before explicitly approving an import:

```bash
zenith skills import docs/examples/analysis-checks.jsonl --approve
zenith skills capacity
zenith skills search --query "ratio denominator" --limit 25
zenith skills show x-checks-ratio-review
```

Then sign in, search the installed library in the Skills dialog and choose a
profile, or use `/skill x-checks-ratio-review` in a conversation. The existing
bounded bundled list stays available. Imported search uses SQLite FTS5 and keyset
pagination; the API never sends the entire large library. Use `--after ID` for
the next CLI page. Public search excludes restricted profiles. Security profiles
still require the owner login and a current admin unlock, and **no profile grants
execution permissions**.

A pack is UTF-8 JSONL with an exact version-1 manifest as its first line:

```json
{"kind":"zenith-skill-pack","schema_version":1,"pack_id":"checks","license":"Apache-2.0","source":"local-authored","source_revision":"v1","reviewed":true}
```

Every subsequent line contains exactly the following fields (see the runnable
[example pack](examples/analysis-checks.jsonl)):

- `id`: `x-PACKID-...`, at most 40 lowercase letters/digits/hyphens.
- `name`, `instruction`, `deliverable`, `practice`: nonempty text with limits of
  100, 700, 600 and 600 characters respectively.
- `category`, `access`: `general`/`public` or `security`/`admin`.
- `kind`: `instruction-profile`; `version`: a positive integer.
- `workflow`: 3–5 steps; `checklist`: 2–5 checks, each at most 500 characters.
- `resource_ids`: 1–4 existing bundled resource identifiers, with no duplicates.
  `zenith skills resources` lists them. Resource selection does not fetch URLs.

Pack IDs have 1–12 characters. Sources are `local-authored` or credential-free
HTTPS references without queries or fragments; record an exact source revision.
Supported rights labels are Apache-2.0, MIT, CC0-1.0, CC-BY-4.0 and public-domain.
The operator must actually hold the relevant rights and preserve applicable
attribution/notices; a manifest label is not proof of licensing or expertise.

Each JSON line is limited to 16 KiB, each pack to 128 MiB, and full rendered
guidance to 2,400 characters. Duplicate properties, duplicate IDs, equivalent
normalized workflow content, unknown fields/resources and credential-like
material fail validation. Security classification is operator-reviewed, not an
automatic semantic assessment. Treat imported text as untrusted task guidance;
the model cannot use it to authorize tools or change server privileges.

## Storage, migration and rollback

Normal reads and default startup create no new feature tables. An explicit
preference save adds `response_preferences`; an explicit import adds
`skill_packs`, `skill_pack_profiles` and `skill_pack_fts` in the existing Store
database. There is no duplicate memory database. Imports are streamed and atomic:
an invalid final row rolls back the entire pack. Existing pack IDs cannot be
overwritten silently. FTS5 must be available in the installation's SQLite build.

Back up the account database before a large import and allow space for both the
input and indexed database. Import outside busy write periods: the measured
100,000-profile import held a transaction for about nine seconds on this host.

Remove only the selected pack with:

```bash
zenith skills remove-pack checks --approve
```

Conversations selecting a removed profile fall back to General on their next
request. Previously stored messages remain. Clear preferences through account
settings or `DELETE /api/preferences`. Rolling back the application release
leaves these additive tables unused by older code; do not delete checkpoints,
tokenizers, native runtime state or existing history as part of rollback.

## Actual model size and validation

The preserved trained checkpoint measured **494,032,768 base parameters plus
4,399,104 existing LoRA parameters: 498,431,872 resident tensor parameters**.
This change did not create a 20-trillion-parameter model. Expanding parameter
count would alter the architecture and require a separately designed training
project; it conflicts with preserving the existing model. The System view now
reports measured resident counts when supported, and unknown for unloaded,
remote or packed/quantized models. Multiple model instances are not summed into
a fictional foundation-model size.

Measured locally on the existing CPU environment, 2026-10-29:

| Check | Observed result |
| --- | --- |
| Existing and new root tests | 379 tests, one skip, 58.752 s |
| Temporary 100,000-profile import | 8.894 s; 90,000 public / 10,000 restricted |
| Indexed profile search | 0.596 ms median, nine queries |
| 10,000-row, two-column CSV | 50.234 ms median, five runs; exact expected sums |
| CSV model calls | Zero, including with the actual preserved model loaded |
| Chromium integration | Login, preferences, CSV, imported activation, logout/account isolation passed |
| Actual checkpoint inference | Saved French preference → `Bonjour`; identity, parameters and saved original profile unchanged |

Raw reports: [scale](benchmarks/productivity/scale.json),
[browser](benchmarks/productivity/browser.json),
[preserved checkpoint](benchmarks/productivity/preserved-model.json).
The scale report records individual source hashes; its commit identifies the
unchanged base before this feature commit. Timings describe this new bounded
path on one host, not a measured overall model speedup. No GPU benchmark,
general accuracy improvement, error-rate reduction or 100,000 learned skills
is claimed.

Reproduce the unit/integration and scale checks:

```bash
python -m unittest discover -s tests
python -m scripts.productivity_benchmark --output /tmp/productivity-scale.json
```

For the real browser workflow, use a separate development environment with the
app's test dependencies and `playwright==1.64.1`, install Chromium with
`python -m playwright install --with-deps chromium --only-shell`, then run
`python -m scripts.smoke_productivity_ui --output /tmp/productivity-browser.json`.
The browser's chat provider is explicitly a fixture; the separate
`scripts.smoke_personalized_model` test requires a verified inference identity
and performs actual checkpoint inference. CI runs it on Linux, Windows and Mac
using the existing independent frozen inference environment. These optional
test SDKs are not added to normal installation requirements.
