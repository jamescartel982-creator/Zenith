# Third-party model support and reference sources

These files are copied for local integration and reference; no upstream code is automatically executed. Complete pinned manifests live under `agent/model_packs/`. Source branding, authorship, licenses and compatibility identifiers are retained. Zenith's new integration code is separate.

- **Zenith 27B**: N8STORM/Qwen3.8-27B-GGUF, revision `3a8bae812a24823b73a83911005f096462237582`. Model-card license: Apache-2.0; Qwen authorship and Unsloth quantization references retained. Apache-2.0 text is available in the root project LICENSE.
- **Zenith Vision**: N8STORM/DeepSeek-V4-Flash-Vision-Exp, revision `aeb503a06a451511bbe64eb42c0cce0a0f63f214`. MIT; copyright (c) 2023 DeepSeek. Full upstream LICENSE retained in `zenith-vision/LICENSE`.
- **Zenith 9B**: N8STORM/Qwythos-9B-Claude-Mythos-5-1M-GGUF, revision `82c035e532112a6c910dba87ade230948ae8a29b`. Model-card license: Apache-2.0; Qwen, Empero and quantization attribution retained. Source naming does not establish any Anthropic affiliation.

Zenith modification: each pack's `.gitattributes` has final overrides that disable Git LFS and text conversion for these vendored support files. The pinned downloader retrieves the original upstream version. All other copied support files are unchanged and verified against their source integrity identifiers. No provider credential was found by the credential-pattern scan performed before bundling. Public documentation/image URLs may contain public asset query identifiers; these are not AI API credentials.

These repositories include 89 weight artifacts totaling about 685.6 GiB across alternative quantizations. Those weights remain external downloads; they are not copied into this Git repository. All 132 upstream paths are accounted for in the manifests. Upstream performance reports are retained as upstream documents, not endorsed benchmark results.
