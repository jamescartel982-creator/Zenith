# Measured recipe-search planning update

SQLite was choosing a broad audience index for selective subject searches in
the 100,000-recipe library. Collecting statistics with `ANALYZE generated_recipes`
lets the planner use actual dimension cardinalities, including 100 subjects and
four audiences. New installs collect these statistics in the installation
transaction. Existing libraries can explicitly refresh them:

```bash
zenith skills recipes optimize --approve
```

This updates only SQLite's recipe planner metadata. The grammar, all 100,000
recipe entries, public/owner access checks, other tables and model remain intact.
There is no new dependency or model training. A complete matching recipe library
is required. The command is local-only and requires explicit operator approval.
Existing installations are not modified just by starting the app.

## Paired measurements

Both sides used identical 100,000-entry data, schema, grammar and search code.
The baseline had default query estimates, matching commit
`c11ecbce87fb50ca8c5641f6ce111c382a3cac97`. The candidate had collected recipe
statistics. The benchmark verifies the search method matches that commit,
alternates execution order, warms each case three times, and checks every JSON
result for equality. It also checks public exclusion of protected recipes,
pagination and the unchanged full recipe digest.
The timed operation is the internal catalog search after the caller's permission
decision; HTTP authentication and neural inference are not included.

The confirmation run used 31 timed samples per side per case on the existing
two-CPU-quota, 8 GiB, CPU-only execution environment. Median milliseconds:

| Query / scope | Default estimates | Collected statistics | Baseline / candidate |
| --- | ---: | ---: | ---: |
| Python correctness beginner | 2.881 | 1.406 | 2.05× |
| Python compare correctness beginner | 6.787 | 1.331 | 5.10× |
| Algebra correctness beginner | 1.264 | 1.363 | 0.93× |
| Data quality reproducibility reviewer | 8.309 | 1.433 | 5.80× |
| Generated, first public page | 0.781 | 0.904 | 0.86× |
| Generated, near public end cursor | 1.041 | 0.978 | 1.06× |
| Exact protected ID, authorized | 0.871 | 0.835 | 1.04× |
| Exact protected ID, ordinary account | 0.679 | 0.817 | 0.83× |

The three selective Python/data searches improved by roughly 2–5.8× in this run.
Other cases did not consistently benefit and some were slightly slower.
The earlier 15-sample trial also recorded a larger slowdown for an empty protected
result; both trials are retained rather than selecting only favorable results.
Shared-host timing variation remains, and these millisecond measurements do not
establish general inference, throughput or whole-system gains.

The captured actual Python query plan changes from `generated_recipe_audience`
to `generated_recipe_subject`. No forced index hint, answer cache, result limit
change, authorization shortcut or search-code change is used.

Raw reports: [first trial](paired-first.json), [31-sample confirmation](paired-confirmation.json),
[application to the normal local Store](local-application.json). Reports record
source hashes and individual samples. Their source commit identifies the unchanged
base before this feature commit; hashes identify the measured implementation.
The local application receipt verifies unchanged data tables, configuration,
checkpoint identity and 100,000 retained recipes. No private DB or credentials
are committed.

Local verification: 390 root tests, one skip; 11 generated-library tests include
maintenance authorization, result stability, unrelated table statistics and
history preservation, reset and missing-library behavior. CI runs paired search
acceptance in addition to existing browser, authorization and real-model checks.

## Reproduce and roll back

Run from a full Git checkout with the app installed:

```bash
python -m scripts.recipe_search_benchmark --samples 31 --output /tmp/recipe-search.json
```

This uses temporary, test-owned databases and does not change the installed
library. No language model is invoked. SQLite version, host details and source
hashes are included in the report. Virtualized timing is reported without a
universal speed threshold.

To restore default query estimates on an installed library:

```bash
zenith skills recipes optimize --reset --approve
```

Only `generated_recipes` rows in SQLite's `sqlite_stat1`/`sqlite_stat4` metadata
are removed; other tables' statistics remain. The existing Store opens a fresh
connection per operation, so subsequent searches see the reset. No recipe,
account, conversation, model or tokenizer deletion is needed. Reverting this
code release alone retains collected statistics; use the reset command before
reverting if the metadata should also be rolled back.

## Parameter and speed targets

This update does **not** add two trillion parameters or make Zenith 10,000×
faster. The last verified preserved checkpoint contains 498,431,872 parameters,
including its existing LoRA adapter. A two-trillion-parameter addition requires
roughly 4 TB just for 16-bit parameter storage, before training state, inference
cache and the existing model. This environment has no GPU and 8 GiB RAM. Such an
expansion needs a separately designed, funded distributed-training project and
new validated checkpoints. A configuration number or generated recipes do not
create trained parameters. Original weights and architecture remain unchanged.
