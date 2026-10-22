# Validation performed

Validated on 2026-10-22 in a Linux CPU environment. These are implementation checks, not a benchmark of general intelligence.

## Local installation update (0.4)

- **63 tests passed** with CPU model dependencies, including profile preservation, configuration precedence, stable user directories, command dispatch, model cache checks, installer failure handling, and corrected-answer approval.
- A fresh Linux installation succeeded in a virtual-environment path containing spaces. Re-running the installer preserved the profile and passed dependency checks.
- The installed wheel ran from another working directory without activation: version, catalog validation, JSON diagnostics, and terminal exit all passed. The packaged catalog retained exactly 1,000 model and 200 dataset sources.
- Real cached CPU inference through both `doctor --inference` and terminal chat returned “2 plus 2 equals 4.” A real localhost browser server passed health and UI checks.
- Python compilation, Bash syntax checks, and Git whitespace checks passed.
- [Hosted Windows/Linux CI](https://github.com/jamescartel982-creator/Zenith/actions/runs/39775105965) passed all six jobs: Python 3.10/3.12 lightweight tests on each OS, plus a full native installation/inference job on each OS. Both native jobs installed in a path containing spaces, downloaded the pinned checkpoint, passed all 63 tests with CPU dependencies, generated a real answer, started the localhost server, and exercised the installed wheel from another working directory. Windows also exercised the PowerShell 5.1 wrappers.
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

- **78 CPU-enabled tests passed**, including local account password/session handling, failed-login limits, same-origin writes, server access gating, user-owned conversation reads/reviews/deletion, persistent private memories, forgetting, bounded memory context, exact pack inventories, all vendored support-file hashes, atomic verified downloads, and the key-free local server request contract.
- A real browser account saved a telescope-project memory; the cached small Qwen CPU model answered **“Your telescope project is called Violet.”** Greeting and history survived reload. Chromium checks covered account creation, sign-out, failed login, conversation navigation, memory controls, three-pack discovery, Markdown/code blocks, safe literal HTML rendering, and desktop 1440×1000/mobile 390×844 layout. No page JavaScript errors or mobile horizontal overflow were observed.
- Public Hugging Face metadata at pinned revisions accounts for all **132 files** across the three requested repositories. All **43 support/source files** were copied and source hashes verified; the only deliberate adaptations are local Git-filter settings in the three `.gitattributes` files. A credential-pattern scan found no provider API keys in the copied files. A real `packs download zenith-9b --support-only` and subsequent pinned integrity verification both succeeded.
- The approximately **685.6 GiB of alternative weight artifacts were not downloaded** into this workspace. The three requested large checkpoints have not been executed, jointly coordinated, or benchmarked here. Local server protocol tests do not establish their hardware compatibility or performance. The current chat transport accepts text, not image attachments.
- No claim is made that this release outperforms Claude or changes a model's training provenance through branding. Required third-party attribution and machine-readable model identifiers are preserved.
