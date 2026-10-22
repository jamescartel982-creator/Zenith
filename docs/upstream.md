# Upstream references and licenses

Zenith uses maintained open-source libraries rather than copying unrelated repositories into a single model. GitHub hosts model implementations and tools; pretrained weights are normally distributed separately through Hugging Face or Ollama. Model outputs, adapters, and training data retain their own provenance and obligations.

| Component | Source | License / use |
| --- | --- | --- |
| Original Zenith starter | https://github.com/jamescartel982-creator/Zenith | Apache-2.0; original LICENSE and ZIP retained |
| Qwen2.5 model family | https://github.com/QwenLM/Qwen2.5 | See each checkpoint's model card; listed defaults are Apache-2.0 |
| Default chat weights | https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct | Apache-2.0; downloaded at runtime |
| Coding model option | https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct | Apache-2.0; optional, not downloaded by default |
| Transformers | https://github.com/huggingface/transformers | Apache-2.0; model loading, templates, Trainer |
| PEFT | https://github.com/huggingface/peft | Apache-2.0; LoRA adapters |
| PyTorch | https://github.com/pytorch/pytorch | BSD-style license; tensor/autograd/attention kernels |
| Ollama | https://github.com/ollama/ollama | MIT runtime; bundled model licenses vary |
| FastAPI | https://github.com/fastapi/fastapi | MIT; local web service |

Implementation references:

- [Qwen model's official inference example](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct).
- [Transformers 4.57 chat templates](https://huggingface.co/docs/transformers/v4.57.1/en/chat_templating).
- [PEFT LoRA guide](https://huggingface.co/docs/peft/en/developer_guides/lora).
- [Ollama chat API](https://docs.ollama.com/api/chat).

`agent/tiny.py` is a new, small implementation of the standard decoder-only transformer architecture. It does not incorporate pretrained weights or claim a novel architecture. Training from random initialization makes it a separate model; LoRA produces an adaptation of an existing base model.
