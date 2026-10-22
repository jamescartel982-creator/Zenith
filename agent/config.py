"""Validated environment settings. No model is loaded during import."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

from .paths import config_file, default_data_dir, zenith_home

# Explicit environment > current checkout .env > saved user configuration.
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
load_dotenv(config_file(), override=False)


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "ensemble").lower())
    team_config: str = field(default_factory=lambda: os.getenv("ZENITH_TEAM_CONFIG", ""))
    knowledge_limit: int = field(default_factory=lambda: int(os.getenv("ZENITH_KNOWLEDGE_LIMIT", "3")))
    model: str = field(default_factory=lambda: os.getenv("HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"))
    revision: str = field(default_factory=lambda: os.getenv("HF_REVISION", "main"))
    adapter: str = field(default_factory=lambda: os.getenv("ZENITH_ADAPTER", ""))
    device: str = field(default_factory=lambda: os.getenv("ZENITH_DEVICE", "auto"))
    data_dir: str = field(default_factory=lambda: os.getenv("AGENT_DATA_DIR", default_data_dir()))
    api_token: str = field(default_factory=lambda: os.getenv("ZENITH_API_TOKEN", ""))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    tiny_checkpoint: str = field(default_factory=lambda: os.getenv("ZENITH_TINY_CHECKPOINT", str(zenith_home() / "artifacts" / "tiny" / "model.pt")))
    max_new_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_NEW_TOKENS", "256")))
    context_tokens: int = field(default_factory=lambda: int(os.getenv("CONTEXT_TOKENS", "2048")))
    cpu_threads: int = field(default_factory=lambda: int(os.getenv("ZENITH_CPU_THREADS", str(min(4, os.cpu_count() or 1)))))
    offline: bool = field(default_factory=lambda: os.getenv("HF_HUB_OFFLINE", "").lower() in {"1", "true", "yes"})
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.4")))

    def __post_init__(self):
        if not 1 <= self.cpu_threads <= 64:
            raise ValueError("ZENITH_CPU_THREADS must be between 1 and 64")
        if self.provider not in {"ensemble", "huggingface", "ollama", "tiny"}:
            raise ValueError("AI_PROVIDER must be ensemble, huggingface, ollama, or tiny")
        if not 0 <= self.knowledge_limit <= 5:
            raise ValueError("ZENITH_KNOWLEDGE_LIMIT must be between 0 and 5")
        if not 1 <= self.max_new_tokens <= 4096:
            raise ValueError("MAX_NEW_TOKENS must be between 1 and 4096")
        if self.context_tokens < 128 or self.context_tokens > 32768:
            raise ValueError("CONTEXT_TOKENS must be between 128 and 32768")
        if not 0 <= self.temperature <= 2:
            raise ValueError("TEMPERATURE must be between 0 and 2")
        if self.device not in {"auto", "cpu", "cuda", "mps"}:
            raise ValueError("ZENITH_DEVICE must be auto, cpu, cuda, or mps")

    @property
    def model_name(self):
        if self.provider == "ensemble":
            return "Zenith model team"
        return self.ollama_model if self.provider == "ollama" else self.tiny_checkpoint if self.provider == "tiny" else self.model
