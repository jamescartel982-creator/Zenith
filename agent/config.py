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
    checkpoint_receipt: str = field(default_factory=lambda: os.getenv('ZENITH_CHECKPOINT_RECEIPT', ''))
    device: str = field(default_factory=lambda: os.getenv("ZENITH_DEVICE", "auto"))
    data_dir: str = field(default_factory=lambda: os.getenv("AGENT_DATA_DIR", default_data_dir()))
    api_token: str = field(default_factory=lambda: os.getenv("ZENITH_API_TOKEN", ""))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    local_server_url: str = field(default_factory=lambda: os.getenv('ZENITH_LOCAL_SERVER_URL', 'http://127.0.0.1:8080/v1').rstrip('/'))
    local_server_model: str = field(default_factory=lambda: os.getenv('ZENITH_LOCAL_SERVER_MODEL', 'zenith'))
    display_name: str = field(default_factory=lambda: os.getenv('ZENITH_MODEL_LABEL', 'Zenith'))
    response_mode: str = field(default_factory=lambda: os.getenv('ZENITH_RESPONSE_MODE', 'fast'))
    reply_style: str = field(default_factory=lambda: os.getenv('ZENITH_REPLY_STYLE', 'auto'))
    fast_max_new_tokens: int = field(default_factory=lambda: int(os.getenv('ZENITH_FAST_MAX_NEW_TOKENS', '96')))
    fast_history_turns: int = field(default_factory=lambda: int(os.getenv('ZENITH_FAST_HISTORY_TURNS', '4')))
    calibration_file: str = field(default_factory=lambda: os.getenv('ZENITH_CALIBRATION_FILE', ''))
    abstain_threshold: float = field(default_factory=lambda: float(os.getenv('ZENITH_ABSTAIN_THRESHOLD', '0.6')))
    tiny_checkpoint: str = field(default_factory=lambda: os.getenv("ZENITH_TINY_CHECKPOINT", str(zenith_home() / "artifacts" / "tiny" / "model.pt")))
    max_new_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_NEW_TOKENS", "256")))
    context_tokens: int = field(default_factory=lambda: int(os.getenv("CONTEXT_TOKENS", "2048")))
    cpu_threads: int = field(default_factory=lambda: int(os.getenv("ZENITH_CPU_THREADS", str(min(4, os.cpu_count() or 1)))))
    offline: bool = field(default_factory=lambda: os.getenv("HF_HUB_OFFLINE", "").lower() in {"1", "true", "yes"})
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.4")))

    orchestration_mode: str = field(default_factory=lambda: os.getenv('ZENITH_ORCHESTRATION_MODE', 'native'))
    reasoning_effort: str = field(default_factory=lambda: os.getenv('ZENITH_REASONING_EFFORT', 'standard'))
    allow_external: bool = field(default_factory=lambda: os.getenv('ZENITH_ALLOW_EXTERNAL', '').lower() in {'1', 'true', 'yes'})

    # Appended to preserve old positional callers and all native inference defaults.
    platform: 'PlatformConfig' = field(default_factory=lambda: _platform_config())
    allowed_hosts: tuple[str, ...] = field(default_factory=lambda: tuple(
        host.strip().lower() for host in os.getenv('ZENITH_ALLOWED_HOSTS', 'localhost,127.0.0.1,::1').split(',') if host.strip()))
    kv_cache_mb: int = field(default_factory=lambda: int(os.getenv('ZENITH_KV_CACHE_MB','64')))

    def __post_init__(self):
        if type(self.kv_cache_mb) is not int or not 0<=self.kv_cache_mb<=512:
            raise ValueError('ZENITH_KV_CACHE_MB must be 0–512 MiB (0 disables reuse)')
        from .http_security import LOCAL_HOSTS, validate_hosts
        validate_hosts(self.allowed_hosts)
        if any(host not in LOCAL_HOSTS for host in self.allowed_hosts) and len(self.api_token) < 32:
            raise ValueError('Non-loopback allowed hosts require ZENITH_API_TOKEN of at least 32 characters')
        from .task_router import MODES
        if self.orchestration_mode not in MODES or self.reasoning_effort not in {'fast', 'standard', 'deep', 'research'}:
            raise ValueError('Invalid orchestration mode or reasoning effort')
        if self.response_mode not in {'fast', 'thorough'}:
            raise ValueError('ZENITH_RESPONSE_MODE must be fast or thorough')
        if self.reply_style not in {'auto','brief','full'}:
            raise ValueError('ZENITH_REPLY_STYLE must be auto, brief, or full')
        if not 16 <= self.fast_max_new_tokens <= 4096 or not 1 <= self.fast_history_turns <= 12:
            raise ValueError('Use 16–4096 fast output tokens and 1–12 fast history turns')
        if not 0 <= self.abstain_threshold <= 1:
            raise ValueError('ZENITH_ABSTAIN_THRESHOLD must be between zero and one')
        if not 1 <= self.cpu_threads <= 64:
            raise ValueError("ZENITH_CPU_THREADS must be between 1 and 64")
        if self.provider not in {"ensemble", "huggingface", "ollama", "tiny", "localserver", "orchestrated", "reasoning"}:
            raise ValueError("AI_PROVIDER must be ensemble, huggingface, ollama, tiny, localserver, orchestrated, or reasoning")
        from urllib.parse import urlparse
        endpoint = urlparse(self.local_server_url)
        if endpoint.scheme not in {'http', 'https'} or endpoint.hostname not in {'localhost', '127.0.0.1', '::1'} or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or any(c.isspace() for c in self.local_server_url):
            raise ValueError('ZENITH_LOCAL_SERVER_URL must be a loopback HTTP(S) URL without credentials')
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
        if self.provider == 'reasoning':
            return 'Zenith bounded reasoning'
        if self.provider == 'orchestrated':
            return 'Zenith orchestration'
        if self.provider == 'localserver':
            return self.local_server_model
        if self.provider == "ensemble":
            return "Zenith model team"
        return self.ollama_model if self.provider == "ollama" else self.tiny_checkpoint if self.provider == "tiny" else self.model


def _platform_config():
    from .platform_config import PlatformConfig
    return PlatformConfig.from_env()
