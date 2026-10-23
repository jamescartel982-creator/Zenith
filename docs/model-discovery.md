# Discover and save model sources

Zenith provides an offline source catalog and on-demand public discovery. In browser chat, select **Browse catalog**, change **Library** to **Search online**, choose a source, and search. Hugging Face search covers publicly discoverable base checkpoints, fine-tunes, adapters, merges, and quantized repositories. GitHub search returns repositories, which can also be tools, research implementations, or documentation. Search results are source references, rather than verified inference providers.

No source API key is required. Source rate limits, gated or private repositories, deleted records, and search result windows limit coverage. Zenith does not claim an exhaustive mirror. Only the selected search page is requested; installation and ordinary chat do not crawl the Hub or GitHub.

## Terminal discovery

Activate the installed environment first:

```text
zenith discover search --source huggingface --query Qwen
zenith discover search --source huggingface --query "N8STORM"
zenith discover search --source github --query "topic:llm"
zenith discover search --source github --query "fine-tuned language:Python"
```

GitHub supports its official repository qualifiers. Broader queries can return unrelated repositories. Search model names, owners, tasks, or relevant topics, then inspect each original source. Use `--kind dataset` for dataset discovery.

Results are JSON with `entries`, `has_more`, and `next_cursor`. For Hugging Face, pass the returned `next_cursor` with `--cursor` for the next page. For GitHub, increment `--page`. `--page-size` sets the page size within the application limit. The browser maintains continuation cursors when using Next and Previous. Changing a query, source, or resource resets pagination. Search services impose their own windows; narrow your query when a window ends.

The app reads available license, base-model, gating, task, and revision metadata. A **Fine-tuned model** label appears only when the source explicitly declares a fine-tune relationship; absence of a label does not prove that a model is a base checkpoint. Other relationships, such as merges and quantization, remain searchable with original lineage metadata. Popularity does not establish response quality.

## Save a model reference

Replace `OWNER/MODEL` with an existing canonical source identifier:

```text
zenith discover add --source huggingface --id OWNER/MODEL
zenith discover add --source github --id OWNER/REPOSITORY
zenith discover list
zenith catalog --query OWNER/MODEL
```

The command retrieves current public metadata, checks the repository identity, and saves it atomically to `model-library.json` under `ZENITH_HOME` (the normal per-user Zenith directory by default). Re-adding a source refreshes its entry. The local catalog searches those records alongside bundled references. The source inventory and bundled catalog validation remain separate. No weights, Python scripts, README instructions, or credentials are imported or executed. Restart an open catalog search to see newly saved references.

The local library belongs to the operating-system account running Zenith. On a shared server, the terminal operator controls imports; source references saved there are visible through that server's catalog. It is not a per-browser-account private memory store. Do not put private information into library metadata. Public discovery is read-only in the browser and uses the existing server-access authentication gate.

## Run a compatible model

Saving a reference does not change the active runtime. Review the source's model card, license, architecture, memory requirements, and supported inference stack. For a supported full Transformers text checkpoint, edit the saved `config.env`:

```dotenv
AI_PROVIDER=huggingface
HF_MODEL=OWNER/MODEL
HF_REVISION=UPSTREAM_COMMIT_SHA
```

Use the source revision recorded in the imported entry. Environment variables and checkout `.env` settings take precedence over `config.env`; update conflicting overrides too. Restart Zenith and run `zenith doctor --inference`. Direct Hugging Face loading uses safetensors with remote custom code disabled. A discovery record does not override those protections or certify compatibility.

Adapters require their compatible base model and an appropriate adapter configuration; they are not interchangeable with a complete checkpoint. GGUF files require a compatible local server or Ollama setup. Vision, audio, embedding, and other task models require their own runtime integrations; the current chat transport is text-only. GitHub repositories are references until a supported inference endpoint is explicitly configured. See [model packs](model-packs.md) and [configured model teams](model-team.md).

## Offline behavior and failures

- `ZENITH_DISCOVERY_OFFLINE=1` disables online discovery. `HF_HUB_OFFLINE=1` also disables it and keeps supported Hugging Face inference on cached files.
- The bundled catalog and saved model references remain searchable offline.
- Online queries go only to the selected public source. HTTPS certificate verification remains enabled, redirects are not followed, and continuation links are checked against the expected source endpoint.
- The discovery client bounds response size, concurrency, response time, cache size, and page size. Upstream error bodies and internal exception details are not returned to the browser.
- Source errors are explicit; a failed search is not presented as successful empty coverage. Rate limits require waiting or narrower searches. There is no automatic unlimited retry or full-site download.

## API references

Implementation reviewed against the official [Hub API](https://huggingface.co/docs/hub/api), [Hub model listing](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api#huggingface_hub.HfApi.list_models), and [GitHub repository search](https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories) documentation on 2026-10-23.
