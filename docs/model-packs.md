# Zenith model packs: complete inventories and local inference

The three requested public Hugging Face repositories are integrated as **Zenith 27B**, **Zenith Vision**, and **Zenith 9B**. No API key is copied or required by the local model-server provider or public-file downloader. These are integrations and local display aliases, not newly trained foundation models.

| Pack | Source repository | Files | All variants |
| --- | --- | ---: | ---: |
| `zenith-27b` | N8STORM/Qwen3.8-27B-GGUF | 33 | 439.65 GiB |
| `zenith-vision` | N8STORM/DeepSeek-V4-Flash-Vision-Exp | 84 | 156.31 GiB |
| `zenith-9b` | N8STORM/Qwythos-9B-Claude-Mythos-5-1M-GGUF | 15 | 89.64 GiB |

All **132 files** are inventoried at pinned commits in `agent/model_packs/`, with exact source names, sizes, Git blob identifiers and, for LFS payloads, SHA-256 hashes. All **43 non-weight support files** are copied under `vendor/model-packs/`, including the DeepSeek reference code, tokenizer, examples, fixtures and MIT license. Each pack's `.gitattributes` is adapted to store vendored support files as ordinary Git blobs without LFS/line-ending filters; other support-file contents match their pinned source hashes. The installed wheel contains the manifests and integration code. Upstream reference files are available in the Git checkout or through `packs download --support-only`.

The **89 weight files are not bundled into Git or downloaded automatically**: the full set is about 685.6 GiB and contains many mutually exclusive quantizations. The development workspace cannot hold that set. A complete download command is supplied below; nothing is represented as downloaded merely because it is inventoried. The 1,000-model popularity catalog remains unchanged; these three packs are a separate requested integration collection.

## Use the installed command

In the examples below, replace `zenith` with `./run.sh` on Linux or `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1` on Windows. An activated `.venv` also exposes the short `zenith` command.

```text
zenith packs list
zenith packs files zenith-9b
zenith packs download zenith-9b
zenith packs verify zenith-9b
```

The default download selects the recommended single text GGUF: about 5.24 GiB for Zenith 9B. Zenith 27B's default selects its Q4_K_M quantization, about 16 GiB. Adjust the exact file after inspecting `packs files`. Available RAM must also cover the runtime and KV cache; a claimed million-token context is not a practical default on a laptop.

Full downloads include every variant, tokenizer, source file, example, projector, and MTP file:

```text
zenith packs download zenith-27b --all --directory /large-disk/zenith-27b
zenith packs download zenith-vision --all --directory /large-disk/zenith-vision
zenith packs download zenith-9b --all --directory /large-disk/zenith-9b
zenith packs verify zenith-9b --all --directory /large-disk/zenith-9b
```

Use a Windows path such as `D:\ZenithModels\zenith-9b` on Windows. Without `--directory`, downloads go to `ZENITH_HOME/models/<pack>`. `--support-only` selects all non-weight files; `--file <exact-name>` selects one inventoried file. Downloads verify size and pinned integrity hashes before atomic replacement, reject unsafe paths, and check free disk space. A failed transfer leaves any existing final file intact. The downloader never imports or executes source code and never reads a provider API key. Original paths are retained so shards, indexes, tests and references stay consistent.

## Run GGUF text chat locally

Install a current compatible [llama.cpp](https://github.com/ggml-org/llama.cpp) build for Windows/Linux with support for the pack's architecture (`qwen35`). The Zenith installer can install the lightweight client using `--mode localserver`; it does not install a GPU driver or silently build arbitrary upstream kernels.

After downloading one ordinary text GGUF, start its runtime in another terminal. Substitute your actual absolute path:

```text
llama-server -m /absolute/path/to/model.gguf --alias zenith --host 127.0.0.1 --port 8080 -c 8192
```

Use `llama-server.exe` and a quoted Windows path on Windows. Start conservatively with a context that fits your hardware. Ordinary non-MTP quantizations are recommended for initial compatibility. Configure Zenith deliberately (this replaces the saved profile; `.env` and external variables still take precedence):

```text
zenith packs configure zenith-9b --overwrite-config
zenith doctor
zenith doctor --inference
zenith serve
```

The provider sends the normal chat-completions request to `http://127.0.0.1:8080/v1` using the local server's `zenith` alias, without an Authorization header or API key. `--endpoint` and `--model-alias` can select another loopback server. Remote hosts and credentials embedded in URLs are rejected. Source IDs stay in provenance and diagnostics; user-facing pack names say Zenith.

## Vision and specialized runtimes

Zenith Vision's source reference calls for specialized DeepSeek V4 Vision kernels and multi-GPU hardware; its upstream example uses four GB300 GPUs. It is not compatible with simply setting `HF_MODEL` in this application's pinned Transformers 4 family. Read the bundled upstream instructions and provision a compatible vLLM/SGLang/reference runtime separately. Expose a compatible local chat-completions endpoint with served model name `zenith`, then select `zenith packs configure zenith-vision --overwrite-config`.

This release's chat transport is **text-only**. A repository's vision tags/projector files do not mean Zenith can accept image attachments. The reference vision source and files are included/inventoried for a future image-input implementation. The three large checkpoints have not been executed or benchmarked in this development environment; the local server protocol, complete inventories, support-file copies, and verified downloader are tested separately.

## Branding and attribution

The app uses Zenith display names and a Zenith system identity. Copyright notices, license text, source filenames/URLs, model architecture identifiers, tokenizer tokens/templates, and binary model metadata retain their original identifiers. Blindly replacing these strings would break loading or remove required attribution; the models' training provenance also cannot be changed by renaming files. A base model can still reproduce its learned identity. Third-party model-card benchmarks remain upstream claims, not Zenith validation results. See `vendor/model-packs/NOTICE.md`.
