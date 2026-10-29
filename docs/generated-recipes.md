# Generated workflow recipe library

Zenith can explicitly install **100,000 labeled generated workflow recipes**.
They combine 100 authored subjects, 25 workflow templates, 10 review lenses and
four audience adaptations. These are instructions, not 100,000 independently
learned, evaluated or certified abilities. No external model outputs, training
corpus, new parameters or executable plugin packages are used.

## Install and use

After updating the application, use its existing virtual environment:

For an existing checkout, run `git pull` and rerun the normal installer before
using a newly added command (`python3 install.py --mode local` on Linux,
`py -3.12 install.py --mode local` on Windows, or `bash install.sh --mode local`
on supported Macs). Existing saved provider settings are preserved unless you
explicitly request replacement. Keep your configured external mode on Intel Macs.

```bash
zenith skills recipes install --approve
zenith skills recipes status
zenith skills search --query "Python correctness beginner" --limit 25
zenith skills show x-recipes-25000
```

From a source checkout, the normal launchers also work:

```bash
bash run.sh skills recipes install --approve
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 skills recipes install --approve
```

In browser chat, sign in, open **Skills**, search and inspect a generated recipe,
then choose Use. Or type `/skill x-recipes-25000` to select the Python explanation
recipe for the current conversation. `/skill off` returns to General. The
composer, search cards, profile details and model instructions identify generated
content. `/skill list` stays bounded and reports the visible generated count;
it does not load all recipes into the prompt or browser.

`recipes status` is a local operator command and reports the actual total.
Public catalog/API counts are role-filtered: **90,000 public recipes** are visible
to a signed-in ordinary account. **10,000 defensive security recipes** remain
hidden and inaccessible until the owner signs in and unlocks Admin. Unlocking
does not select a recipe or grant execution capabilities. Existing per-tool
permissions, authorization scope, MFA and emergency controls still apply.

The existing 32 curated profiles remain separate. Installation is an explicit
local action, not a startup migration or automatic network fetch. The installed
catalog has a shared 100,000-entry limit: a full recipe library leaves no capacity
for imported packs. If imported profiles occupy that capacity, installation
fails and preserves them. It never deletes another pack to make room.

## What the generator does

The frozen [v1 grammar](../agent/recipe_definitions_v1.py) defines:

- 100 subject contexts covering mathematics, science, programming, infrastructure,
  AI, data analysis, writing, planning, financial education and defensive security.
- 25 tasks including explanation, comparison, evidence review, dependency mapping,
  debugging, evaluation planning, uncertainty analysis and handoff preparation.
- 10 review lenses including correctness, reproducibility, privacy, failure modes
  and authorization.
- Four audience instructions: beginner, practitioner, reviewer and decision maker.

Every combination changes model guidance, including audience adaptation.
Installation rejects duplicate normalized instructions; titles alone cannot
inflate the count. Each recipe has a stable ID, title, bounded instruction,
five workflow steps, three checks, a deliverable, practice guidance and a reference
to existing resource metadata. Resource links are not fetched on installation or
selection. They support learning; they do not validate a recipe or its answers.

The deterministically authored grammar is Apache-2.0 under Zenith's existing
license. Structural validation, secret-pattern screening, reference checks and
duplicate checks run on **all 100,000 entries**. These do not constitute
individual human review or evaluation of 100,000 task outcomes.

## Compact persistence and search

All 100,000 entries are stored as versioned coordinates in the existing SQLite
Store. SQLite indexes and a small FTS5 index over grammar dimensions support
bounded search. Full prose is rendered for requested results and the selected
recipe. There is no duplicated JSONL file or second memory database.
Search matches subject, task, review and audience descriptors, or an exact recipe
ID. It is lexical descriptor search, not semantic retrieval over arbitrary prose.
User text becomes quoted search terms, not SQL or FTS operators.

The additive tables are `generated_recipe_packs`, `generated_recipes` and
`generated_recipe_terms`, plus indexes. Creation and insertion happen in one
transaction. A validation failure rolls back the new tables and rows.
Installation records the definition SHA-256 and a digest of all rendered profiles.
Rendering refuses a changed definition fingerprint instead of silently changing
an installed recipe. Keep v1 frozen: a future grammar needs its own version and
explicit migration.

Allow at least 64 MiB free disk space. The measured database was about 7.3 MiB,
with temporary transaction/index overhead during installation. The write
transaction lasts several seconds; install outside busy write periods. Account
data, memories, settings, model weights, tokenizer and native runtime state remain
separate from this installation.

## Removal and rollback

```bash
zenith skills recipes remove --approve
```

This removes generated recipe entries and metadata/index content. Existing
conversations and imported/bundled profiles remain. A conversation selecting a
removed recipe falls back to General on its next request. Installing an intact,
matching pack is idempotent. Definition mismatch or an incomplete pack requires
explicit removal/restoration; it is never silently overwritten.

Back up the account database before installing a release. Reverting code leaves
the additive tables unused by older code. SQLite may retain free pages after
removal; deletion does not promise to shrink the database file. Do not delete the
user database or model files to roll back.

## Reproduce validation

```bash
python -m unittest discover -s tests -p test_generated_recipes.py -v
python -m scripts.generated_recipes_acceptance --output /tmp/generated-recipes.json
python -m scripts.smoke_productivity_ui --generated-recipes --output /tmp/generated-browser.json
```

The browser test needs the optional Playwright setup described in
[productivity](productivity.md). Its chat provider is an explicit fixture.
The separate `scripts.smoke_personalized_model --generated-recipes` test uses
the verified checkpoint, selects an installed recipe and checks a real Python
arithmetic response, alongside parameter/tokenizer/profile preservation. CI runs
it on Linux, Windows and macOS ARM64.

Raw measurements and source hashes:
[installation/search](benchmarks/generated-recipes/acceptance.json),
[browser](benchmarks/generated-recipes/browser.json),
[preserved model](benchmarks/generated-recipes/preserved-model.json).
The separate [local installation receipt](benchmarks/generated-recipes/local-installation.json)
records durable installation into this execution environment's configured Store,
with original tables, configuration and checkpoint unchanged and SQLite integrity
verified. This is not a claim of installation on another person's computer or a
remote production host. No private user data, database, credentials or model
weights are committed.

Local results on 2026-10-29:

| Check | Observed result |
| --- | --- |
| Full root regression suite | 388 tests, one skip |
| Bridge regressions | 33 passed |
| Generated/access-control focused regressions after command message change | 24 passed |
| Temporary full-library install | 5.440 s; 100,000 actual rows; 7,634,944-byte database |
| Five descriptor/ID searches | 1.502 ms median; individual samples recorded |
| Normal local Store installation | 5.553 s; 100,000 entries; 7,749,632-byte database |
| Real Chromium | Generated label, selection, account isolation and CSV checks passed |
| Preserved checkpoint | Selected recipe answered Python arithmetic with `4`; parameter/profile hashes unchanged |

These are specific functional checks, not general intelligence benchmarks.
No 20-trillion-parameter model or 10,000× overall speedup is claimed.
