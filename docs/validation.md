# Validation performed

Validated on 2026-10-22 in a Linux CPU environment. These are implementation checks, not a benchmark of general intelligence.

## Local installation update (0.4)

- **63 tests passed** with CPU model dependencies, including profile preservation, configuration precedence, stable user directories, command dispatch, model cache checks, installer failure handling, and corrected-answer approval.
- A fresh Linux installation succeeded in a virtual-environment path containing spaces. Re-running the installer preserved the profile and passed dependency checks.
- The installed wheel ran from another working directory without activation: version, catalog validation, JSON diagnostics, and terminal exit all passed. The packaged catalog retained exactly 1,000 model and 200 dataset sources.
- Real cached CPU inference through both `doctor --inference` and terminal chat returned “2 plus 2 equals 4.” A real localhost browser server passed health and UI checks.
- Python compilation, Bash syntax checks, and Git whitespace checks passed.
- [Hosted Windows/Linux CI](https://github.com/n8storm/Zenith/actions/runs/39775105965) passed all six jobs: Python 3.10/3.12 lightweight tests on each OS, plus a full native installation/inference job on each OS. Both native jobs installed in a path containing spaces, downloaded the pinned checkpoint, passed all 63 tests with CPU dependencies, generated a real answer, started the localhost server, and exercised the installed wheel from another working directory. Windows also exercised the PowerShell 5.1 wrappers.
- A separate clean Ollama-mode Linux installation and repeat default-mode upgrade preserved its Ollama profile and omitted Torch/Transformers. Ollama server inference remains outside the checks performed.

## Automated checks

`python -m unittest discover -s tests -v`: **19 tests passed** with local inference dependencies installed.

Coverage includes conversation persistence/isolation, cross-session feedback rejection, explicit approval and revocation, corrected-answer export, deletion, real chat message roles, bounded generation admission, failure handling, context trimming, grouped train/evaluation splitting, assistant-only loss masking, EOS versus padding labels, causal attention, backpropagation, checkpoint reload, and static UI/API authentication.

`python -m compileall -q agent scripts tests` completed. Public startup without a long access token correctly exited with a configuration error.

## Real inference and browser

Downloaded and loaded `Qwen/Qwen2.5-0.5B-Instruct` at Hub revision `7ae557604adf67be50417f59c2c2f167def9a775` using safetensors, without remote custom code.

- Direct chat answered a greeting and returned “The answer to 2 + 2 is 4.”
- Browser chat through the real API returned “2 plus 2 equals 4.”
- Chromium automation exercised sending, review approval, persistence after reload, and a new isolated conversation.
- Desktop 1440×1000 and mobile 390×844 screenshots were inspected/generated. No uncaught page JavaScript errors or mobile horizontal overflow were observed.

## Training and adapters

A **synthetic plumbing fixture**, not user conversation data, supplied ten independent short math prompts: eight train and two evaluation examples. Ran one CPU LoRA optimizer step with rank 8/all-linear, max length 256, batch size 1, accumulation 1.

- Adapter and tokenizer were saved.
- Baseline evaluation loss: approximately **2.6363**.
- Candidate evaluation loss: approximately **1.7497**.
- Adapter loaded back through Zenith and generated text.
- Standalone adapter loss evaluation completed.

This tiny check cannot establish useful improvement. A sampled adapter response was incorrect despite reduced fixture loss. The candidate was **not promoted to the default**. Use substantial representative held-out evaluation and manual checks before choosing an adapter.

Zenith Tiny also trained for ten CPU steps using a synthetic repeated text corpus, width 32, two layers, two heads, context length 128, and batch size 2. Its 37,536 parameters updated; held-out next-byte loss moved from approximately 5.5561 to 5.2936. Checkpoint saving, loading, and generation were verified. Such a small/repetitive smoke corpus does not produce a useful assistant.

## Docker

Built the supplied CPU image successfully, ran it as its non-root user, mounted a persistent database volume and a read-only cached model, and verified:

- `/healthz` responded and distinguished unloaded/loaded model state.
- An unauthenticated API request returned **401**.
- An authenticated chat request returned **200** and “2 plus 2 equals 4.”

The container test used cached weights in offline mode; the model was downloaded outside the container earlier. Normal first-run download inside a fresh hosted image remains dependent on that host's network and available disk/RAM.

## Versions used

Host: Python 3.12.14, PyTorch 2.14.1+cpu, Transformers 4.57.6, PEFT 0.18.1, FastAPI 0.159.1, Starlette 1.9.0, Pydantic 2.14.1, httpx 0.28.1. The Docker image used Python 3.11 and CPU PyTorch. Requirements constrain supported version families; exact versions may vary on a new installation.

Not verified: GPU/MPS execution, quantized Ollama runtime inference (request contract is tested), larger checkpoints, long-run training quality, multi-user deployment, or a public hosting service. No public Space/server was created, no model was published, and no general capability improvement is claimed.

## Catalog and model-team extension

The 0.3 extension was checked separately on the same date:

- Four source snapshots validate to exactly **500 Hugging Face models, 500 GitHub model repositories, 100 Hugging Face datasets, and 100 GitHub dataset sources**, with per-source identity deduplication and source URLs/provenance. Entries remain metadata references rather than installed/verified models. GitHub query-pool ranking is not a global top-500 ranking.
- **52 offline tests passed**, including nine initial ensemble tests plus cache eviction (10 ensemble checks), registry validation/search/authentication, dataset import limits/format handling, full-text retrieval, database migration, and the original chat/training/transformer checks.
- A real CPU two-model run used **Qwen2.5-0.5B-Instruct** and **SmolLM2-360M-Instruct**. Both drafted, the independent model cross-reviewed both proposals, and Qwen synthesized “The correct answer to 2 plus 2 is 4.” All four calls succeeded; this checks coordination, not general quality improvement.
- Imported two streamed SQuAD rows from the catalog-pinned Hugging Face revision; duplicate shared context became one local document. Imported five CSV rows from a pinned GitHub countries-data commit. These are bounded source-import checks, not ingestion of all 200 collections.
- With the SQuAD context available, the full two-model draft/review/synthesis pipeline answered that Notre Dame's Main Building has the golden statue of the Virgin Mary. The response retained the source link and a non-degraded contribution trace. This CPU check took about 67 seconds with 48 output tokens per stage; production latency varies.
- A browser run during heavy CPU/build contention exceeded the earlier 120-second soft budget, correctly displayed its draft fallback, and preserved source/context history. The default team budget was increased to 300 seconds; it remains a soft boundary between synchronous calls. This does not imply a hard cancellation guarantee.
- Real Chromium browser checks exercised the 1,200-entry catalog, filters, paging, source links, team traces, retrieved source excerpts, history reload, and desktop/mobile layout. The full completed trace rendered correctly after reload. No uncaught JavaScript errors or mobile horizontal overflow were observed.
- The installable wheel includes all four catalog snapshots, ensemble code, web assets, and dataset import utilities.

Only the two small default checkpoints were exercised for real collaboration. The remaining catalog models are not claimed to be loaded, compatible with text chat, benchmarked, or communicating. No aggregate model was trained from all sources, and no dataset payload was included in Git.

The final 0.3 Docker image was also built and run with cached weights in offline mode. Its authenticated catalog reported the exact 1,000/200 counts; an unauthenticated request returned 401. Both default checkpoints drafted, cross-review succeeded, and final synthesis returned “The correct answer to 2 plus 2 is 4.” All four model calls completed successfully. Dataset import utilities and all catalog snapshots are included in that image.

## Memory and requested model packs (0.5)

- **80 CPU-enabled tests passed**, including local account password/session handling, failed-login limits, same-origin writes, server access gating, user-owned conversation reads/reviews/deletion, persistent private memories, forgetting, bounded memory context, exact pack inventories, all vendored support-file hashes, atomic verified downloads, and the key-free local server request contract. Controlled-provider tests exercise three separate local endpoints sharing drafts, cross-review, and synthesis; this is a protocol/orchestration check, not a large-model inference benchmark.
- A real browser account saved a telescope-project memory; the cached small Qwen CPU model answered **“Your telescope project is called Violet.”** Greeting and history survived reload. Chromium checks covered account creation, sign-out, failed login, conversation navigation, memory controls, three-pack discovery, Markdown/code blocks, safe literal HTML rendering, and desktop 1440×1000/mobile 390×844 layout. No page JavaScript errors or mobile horizontal overflow were observed.
- Public Hugging Face metadata at pinned revisions accounts for all **132 files** across the three requested repositories. All **43 support/source files** were copied and source hashes verified; the only deliberate adaptations are local Git-filter settings in the three `.gitattributes` files. A credential-pattern scan found no provider API keys in the copied files. A real `packs download zenith-9b --support-only` and subsequent pinned integrity verification both succeeded.
- The approximately **685.6 GiB of alternative weight artifacts were not downloaded** into this workspace. The three requested large checkpoints have not been executed, jointly coordinated, or benchmarked here. Local server protocol tests do not establish their hardware compatibility or performance. The current chat transport accepts text, not image attachments.
- No claim is made that this release outperforms Claude or changes a model's training provenance through branding. Required third-party attribution and machine-readable model identifiers are preserved.

## Streaming, quality workflow, and owner tools (0.6)

Checked on 2026-10-22. Public-fixture raw reports, generated answers, original frozen pilot data, and hashes are in [benchmarks/v0.6](benchmarks/v0.6/). No private user conversations or owner secrets are included.

- **102 CPU-enabled automated tests passed** locally, including account-bound admin elevation, expiry/rotation/logout, secret rejection before model/history/memory/training corrections, allowlisted tools, human-review ownership/resolution/deletion, exact arithmetic bounds and decimal/fraction preservation, independent calibration contracts, immutable grouped dataset partitions, book snapshot/citation/deduplication, streaming protocol, busy/auth responses, cancellation cleanup, and failure without storing partial text.
- Real Chromium checks at 1440×1000 and 390×844 exercised owner-code recognition without chat storage, the Devil-mode calculator, explicit saved memory with actual CPU generation (**“Your telescope project is called Violet.”**), streaming before completion, a human-review request and admin response, reload, lock, and logout clearing private review views. No page errors or horizontal overflow were observed. First text including cold model load under concurrent test contention took **27.43 seconds**; this is separate from the warmed benchmark below.
- Controlled before/after diagnostics used the same pinned Qwen2.5-0.5B revision `7ae557604adf67be50417f59c2c2f167def9a775`, CPU with two PyTorch threads, temperature 0, 64-token cap, 2,048-token input budget, isolated per-case conversations, and a separate warm-up. This is a single 14-case public development run, not a statistical performance study. The upgraded base profile passed **13/14 rule-scored cases**, with no lower slice accuracy than the earlier baseline. It still falsely called base-60 a duodecimal system; the error is preserved for review.
- Among the **five cases still requiring the model**, median first visible streamed text was **1.25 seconds**, median complete upgraded reply **10.35 seconds**, and the earlier matched median **9.15 seconds**. Full generation did not get faster in this comparison. Across all 14 cases, median request time dropped from **9.53 seconds to 2.86 ms**, because nine questions now use deterministic arithmetic/evidence/application rules. This aggregate figure must **not** be presented as raw LLM throughput improvement. Output lengths and instructions also differ.
- A real 40-step/one-epoch, rank-8 all-linear LoRA pilot trained on **40 examples**, validated on **10**, and evaluated on **10 untouched final-test examples** across ten balanced topics. Training took **85.95 seconds**. Validation loss fell **3.5107 → 2.5624**; independent final-test target loss fell **3.6040 → 2.7143** over 283 target tokens. The dataset is a small original educational fixture, not comprehensive subject training.
- The adapter remains **unpromoted**. Its controlled answer diagnostic passed **12/14** rule-scored cases and triggered a finance slice regression. Manual review identified that the diversification response is a valid but underspecified paraphrase rejected by the keyword scorer; the history answer remained false. An earlier exploratory, temperature-0.4 candidate also invented historical context. These are reasons to inspect complete responses, improve evaluation on a new development version, and avoid promotion from loss alone. The default adapter/profile was not changed.
- All ten starter reference URLs returned HTTP 200 when checked; only small availability/title/hash metadata were retained. A real, bounded Euclid/Casey Gutenberg import downloaded a **1,842,708-byte** HTML snapshot, retained notices/hash, extracted 484,168 characters, and added **85 cited retrieval documents** in an isolated test data directory. This book was **not used for weight training** and was not silently added to users' databases.

The original frozen training source is archived even though a reference-only Investor.gov URL was subsequently corrected in the bundled seed. The original train/validation/final-test hashes still verify. Public diagnostic results informed implementation and therefore are not sealed test evidence. No fitted calibration artifact is activated; ordinary model answers remain uncalibrated. No broad adversarial, subgroup fairness, live trading, external penetration testing, large-pack inference, or universal-knowledge claim is established by these checks.

## Five-component system view and efficiency (0.7)

- **111 CPU-enabled tests passed** locally, including new checks for request budgets, complete recent context pairs, preservation of older stored turns, exact usage persistence, account/owner metric boundaries, bounded retention, like-configuration latency signals, cache reuse across budget changes, provider-reported SSE token counts, and disconnect cleanup. The real browser cancellation check exposed an ASGI send-failure cleanup gap; `ManagedStreamingResponse` now closes the iterator and generation lease explicitly, with a regression test for ASGI 2.4 disconnects.
- A real CPU browser run with `serve --warmup` checked all five components, private metrics, reported token usage, streamed replies, Stop during a detailed generation, absence of the cancelled partial turn after reload, logout clearing metrics, and 1440×1000/390×844 layouts. No page errors or horizontal overflow were observed. The actual factual reply was **“The SI unit of force is the newton (N).”**
- A five-question, warmed before/after run on the same pinned model, two CPU threads, temperature 0, 256-token configured maximum, and 2,048-token input budget used **940 → 555 prompt tokens** and **572 → 120 retokenized visible reply tokens**. Median complete time fell **13.17 → 6.99 seconds**. First visible text median was **1.09 → 1.36 seconds**, and the rainbow case became slower. The output policy intentionally differs. These are small development measurements, not general throughput or ChatGPT/Claude parity evidence.
- A separate public 14-case diagnostic with a 64-token cap retained **13/14** and no slice accuracy regression against v0.6. Five model-generated cases had a **2.61-second** median complete reply and **0.97-second** median first visible text in that run. The base-60 history error remains; an evaporation answer in the separate speed comparison also contains a false explanation. Neither lower token use nor unchanged keyword accuracy certifies factual quality.
- [Raw measurements, answers, browser report, and limitations](benchmarks/v0.7/) are committed. New budget and configuration-signature fields invalidate older calibration artifacts; none is enabled by default. No new training adapter or broader learned expertise is claimed in this release.

The scheduled diagnostic workflow uses the frozen public baseline and isolated CI data; it never reads private production conversations or promotes a model. Production latency alerts are review signals, not an accuracy or fairness drift guarantee. See [system behavior and monitoring limits](system.md).

## Complete file verification and deployment consistency (0.8)

- **116 CPU-enabled tests passed** locally. New checks cover modified/missing source files, required entries, malformed/duplicate manifests, unsafe paths and symlink escape, Windows/Linux newline normalization, changed or unhashed wheel code, editable-install reporting, and Fast-mode diagnostics without an unused reviewer's cache.
- A normal Linux wheel upgrade in a path containing spaces completed with dependency checks and automatic isolated-mode wheel verification. Installed commands, catalog, System, and wheel verification worked outside the checkout. Existing profile/data paths were preserved.
- A real Docker build installed version **0.8.0** and verified the wheel. Its runtime used **UID 1000**, contained all **43 vendored support/source files**, and completed real cached-model inference through the Fast-mode doctor. The temporary container was recreated with the same data volume: account/session, saved memory, owner binding, and the exact protected code file survived; file mode remained **0600**. The fixture code itself was never logged.
- The Docker build layout was consolidated after this environment's VFS storage driver exhausted temporary space by copying large dependency layers. The failed build cache was removed; source/user data and tagged images were retained. The corrected build completed. Reproducible checks are in `scripts/smoke_container.py`; CI runs its persistence checks without downloading model weights, while native install jobs cover real inference.
- The source manifest covers every tracked release file except itself, including code, assets, docs, workflows, installers, tests, catalogs, original starter archive, and vendored support sources. UTF-8 text is normalized only for CRLF/LF portability; binary files retain exact checksums. Installed-wheel checks separately use distribution records. Neither inventory is a publisher signature or a model-quality guarantee.

No prompt/model/training capability improvement is claimed for this maintenance release. Historical v0.7 timing/quality reports retain their original scope. All 89 alternative large-model weight artifacts remain external pinned downloads; no private accounts, keys, conversation databases, or candidate adapters are included in source releases.

## Provider response integrity (0.8.1)

Checked on 2026-10-23. **127 CPU-enabled tests passed** locally, including 11 new protocol and real HTTP tests. A loopback server flushed a small text event and withheld the remainder until the client consumed that first event; the client received the delta without waiting for the remainder. Another real HTTP fixture disconnected before completion: the chat API emitted an error, saved no partial turn, recorded a failed request, released the model lock, and completed the next request successfully.

Additional cases cover split Unicode, BOM/CR/LF/CRLF boundaries, multiline SSE, comments, NDJSON, malformed JSON and text, frame and total byte limits, missing completion markers, provider usage after completion, redirects, connection closure, and cancellation. Existing provider fixtures were updated to supply properly delimited SSE byte events. Python compilation and Git whitespace checks passed.

A normal 0.8.1 wheel upgrade verified **72 hashed installed files**. Installed commands, catalog, diagnostics, and terminal exit succeeded outside the checkout. The refreshed source inventory covers **181 files**, including the transport module, tests, and engineering guide.

These are transport and application integration checks, not actual Ollama/vLLM/llama.cpp model execution or a neural inference benchmark. The read timeout remains 300 seconds of inactivity; cancellation cannot forcibly interrupt a blocking network read. No new model, training adapter, or calibration artifact is activated. See [protocol contracts and operational limits](provider-reliability.md).

## Curated AI and cybersecurity learning library (0.9)

Checked on 2026-10-23. **134 CPU-enabled tests passed** locally, including seven library tests covering 51 profiles, 40 resources, six educational terminology labels, preserved legacy IDs, schema/reference validation, malformed links and metadata, search/category behavior, copy isolation, bounded selected instructions, unchanged general prompts, gated API access, no resource fetching during browsing, no role elevation, and CLI operation without importing Torch.

All **40 original-publisher pages** returned successful live retrievals. Titles, dates, HTTP status, and source URLs are recorded in the bundled library. This verifies point-in-time availability; it is not exhaustive content review, reuse permission, or an assurance that links never change. The release includes original summaries and links rather than copies of source courses or books.

A controlled-provider Chromium check passed at **1440×1000** and **390×844**: 51 grouped options, category filtering, empty search results, workflow and source details, six terminology explanations, selected profile in a real chat request, Escape dismissal, and no page errors, mobile horizontal overflow, or external requests during browsing. Screenshots were visually inspected. This UI fixture does not measure model knowledge.

The pinned small Qwen CPU model retained **13/14** on the public development diagnostic with **no accuracy-regression slices**. General-subject prompts remain compatible; security scope text is applied to the relevant profiles. This diagnostic informed implementation and is not sealed test evidence. The historical base-60 error remains. No new weights, training, professional certification, exhaustive skill coverage, or broad cybersecurity-model compliance claim is established. Profiles are model guidance; application authorization remains separate.

The regular 0.9.0 wheel verified **73 hashed installed files**, including the packaged learning library. Installed skills validation and other command checks succeeded outside the checkout. The source manifest inventories **184 files**; external model weights and private local data remain separate.

## Built-in commands and owner-only security activation (0.10)

Checked on 2026-10-23. **149 CPU-enabled tests passed** locally. Fifteen new authorization/runtime tests cover public command persistence without generation/history, owner-scoped state, direct forged chat/stream fields, locked owners, guests and non-owners, login-hash binding, expiry, lock/logout/rotation, explicit reactivation, revocation during streaming and before save, masked terminal credentials, non-interactive rejection, terminal cleanup, and additive SQLite upgrades/deletion. Earlier library tests now reflect 11 public conversation skills and 16 owner-only security profiles; AI engineering is maintained in code and developer documentation.

A controlled-provider Chromium run passed at **1440×1000** and **390×844**. It verified public commands and reload persistence, no AI engineering selector, failed non-owner unlock despite a correct fixture code, explicit owner activation, server-side selection in the actual chat path, HTTP 403 for forged protected generation, and reset on lock and expiry. There were no page errors, external requests, or horizontal overflow. Screenshots were visually inspected. A separate metadata-failure check blocked generation until the active state was confirmed again, then recovered without a model request.

Security authorization is checked in the backend and core rather than inferred from the model or UI. Partial turns after revocation are discarded. These are account/command and application checks; they do not certify model expertise or offensive capability, and the local OS owner remains trusted. Neural weights and training were not changed. Existing provider cancellation and public diagnostic limits still apply.

A regular 0.10.0 wheel verified **74 hashed installed files**; skills validation and installed commands succeeded outside the checkout. The complete source inventory covers **187 files**, including the new authorization module, runtime tests, and engineering guide. Private login/code files and external weights remain outside source releases.

## Model discovery, pixel identity, and activation (0.11)

Validated on 2026-10-23 in a Linux CPU environment. These checks cover implementation behavior; model discovery does not certify upstream checkpoints or general answer quality.

- The complete CPU-enabled suite passed after the runtime changes. Focused discovery checks cover source identity, fine-tune lineage, bounded responses, cache isolation, continuation-host validation, offline behavior, GitHub search windows, explicit failure codes, corrupted-library handling, and atomic metadata imports. Activation and dependency-report tests distinguish success from real failures.
- Live public Hugging Face search returned model metadata and a distinct continuation page. Live GitHub repository search returned public results. The browser also exercised a live Hub search; controlled browser responses checked Next/Previous cursor handling, reset, fine-tune display, and source failure recovery.
- A clean Linux Ollama-client installation succeeded in an environment path containing spaces. A repeat installation preserved its configuration, verified dependencies, checked installed wheel hashes, and completed diagnostics. The expected warning identified the separately required Ollama server; external Ollama inference was not tested.
- The regular installed wheel passed integrity verification and command, resource, diagnostics, source-catalog, skills, and terminal-exit checks from another directory. Packaged runtime files were compared directly against the current source.
- Chromium desktop and mobile checks passed for initial artwork, signed-in welcome-back branding, reload, source discovery, pagination, source errors, existing skill commands, and streamed chat with a controlled provider. No browser JavaScript errors or horizontal overflow were observed. The terminal and installer share an offline text wordmark; ordinary terminals do not render the browser PNG.
- Python compilation, Bash syntax checks, README local-link checks, and Git whitespace checks passed. The source release inventory is regenerated for this release, including activation helpers, artwork, discovery code, tests, and documentation.
- The release CI workflow includes Python 3.10/3.12 tests on Windows and Linux, native installation with cached-model inference on both platforms, explicit PowerShell 5.1 and Bash activation/deactivation checks, and container/server verification. Hosted run results are linked from the release pull request in [GitHub](https://github.com/n8storm/Zenith/pulls?q=is%3Apr+0.11).

Public source APIs can fail, rate-limit, or return incomplete metadata. Saved references do not download weights, execute source repositories, configure a runtime, or add training knowledge. Full-site mirroring and arbitrary architecture compatibility are outside the implemented behavior.

## Simplified installation and browser launch (0.11.1)

Validated on 2026-10-23. Windows setup now starts through `Install Zenith.cmd`; later sessions use `Start Zenith.cmd`. Linux setup supports `bash install.sh --launch`, followed by `bash start.sh` on later visits. Python remains a prerequisite; normal launchers select the isolated environment automatically.

Focused checks cover selected-interpreter use, model download before launch, installation interruption, external-runtime behavior, launch failure propagation, browser readiness and unavailable-browser fallback, and launch from directories containing spaces. A real local server smoke check records the browser-open request only after its health endpoint responds. Existing installation, account, owner-control, model-provider, data, and evaluation regressions remain in the release suite. Native Windows/Linux CI additionally exercises the browser-ready smoke check; Windows checks CMD launcher argument forwarding and Linux checks its start script.

The auto-open option opens a local URL, rather than signing in or changing credentials. A headless machine can use the printed URL manually. The first installation still requires downloading Python dependencies and configured model weights; duration depends on the connection and hardware.

## Continued-training candidate (0.12.0)

On 2026-10-24, the existing local trained adapter loaded with its pinned original base and tokenizer. Actual CPU continuation, held-out loss evaluation, raw-model answer diagnostics, safe local merge/export, and exported-model reload were performed. Original parent hashes and tokenizer compatibility were preserved. [Full evidence and limitations](continued-training.md) include the interrupted data-isolation run and the corrected scoring method. The candidate failed promotion gates; production remained unchanged.

Local regressions cover existing chat, installation, skills, memories, and owner features, plus Argon2id migration, TOTP enrollment/replay prevention, explicit tool grants, scope rejection before connection, emergency stop, legacy-route enforcement, bounded plan history, held-out replay exclusion, and summary ownership/deletion. Chromium desktop/mobile checks exercised actual setup and interaction with controlled test accounts/providers, with no page errors. Those controlled browser checks do not benchmark model intelligence.

The complete Linux CPU-enabled suite ran 186 tests: 185 passed and one platform-specific check was skipped. The regular wheel passed integrity verification for 87 hashed files and installed-command/resource/browser-ready smoke checks outside the checkout. A separate install into an environment path containing spaces passed dependency and storage diagnostics; its Ollama warning correctly identified the separately required runtime. The source ZIP is verified before review. Hosted Windows/Linux and container validation runs are linked from the release pull request. Previous release results do not establish validation of these changes. Candidate weights remain local and inactive; no new Hugging Face project is created and the production model profile is unchanged.
