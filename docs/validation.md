# Validation performed

Validated on 2026-10-22 in a Linux CPU environment. These are implementation checks, not a benchmark of general intelligence.

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
