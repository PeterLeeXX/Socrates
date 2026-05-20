"""Configuration management."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# load .env from cwd first, then from ~/.socrates/
load_dotenv(Path.cwd() / ".env", override=False)
load_dotenv(Path.home() / ".socrates" / ".env", override=False)


@dataclass(frozen=True)
class ModelSpec:
    litellm_model: str
    provider: str
    env_keys: tuple[str, ...]
    max_tokens: int
    api_base: str | None = None


DEFAULT_MODEL = "deepseek-v4-flash"


MODEL_REGISTRY = {
    # DeepSeek
    "deepseek-v4-flash": ModelSpec("deepseek/deepseek-v4-flash", "deepseek", ("SOCRATES_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"), 1_000_000),
    "deepseek-v4-pro": ModelSpec("deepseek/deepseek-v4-pro", "deepseek", ("SOCRATES_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"), 1_000_000),
    # Qwen / DashScope
    "qwen3.6-plus": ModelSpec("dashscope/qwen3.6-plus", "qwen", ("SOCRATES_QWEN_API_KEY", "QWEN_API_KEY", "DASHSCOPE_API_KEY"), 1_000_000),
    "qwen3.6-flash": ModelSpec("dashscope/qwen3.6-flash", "qwen", ("SOCRATES_QWEN_API_KEY", "QWEN_API_KEY", "DASHSCOPE_API_KEY"), 1_000_000),
    # OpenAI
    "gpt-5.5-pro": ModelSpec("gpt-5.5-pro", "openai", ("SOCRATES_OPENAI_API_KEY", "OPENAI_API_KEY"), 1_000_000),
    "gpt-5.5": ModelSpec("gpt-5.5", "openai", ("SOCRATES_OPENAI_API_KEY", "OPENAI_API_KEY"), 1_000_000),
    "gpt-5.4-pro": ModelSpec("gpt-5.4-pro", "openai", ("SOCRATES_OPENAI_API_KEY", "OPENAI_API_KEY"), 1_000_000),
    "gpt-5.4": ModelSpec("gpt-5.4", "openai", ("SOCRATES_OPENAI_API_KEY", "OPENAI_API_KEY"), 1_000_000),
    # Anthropic
    "claude-opus-4.7": ModelSpec("claude-opus-4-7", "anthropic", ("SOCRATES_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), 1_000_000),
    "claude-opus-4.6": ModelSpec("claude-opus-4-6", "anthropic", ("SOCRATES_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), 1_000_000),
    "claude-sonnet-4.6": ModelSpec("claude-sonnet-4-6", "anthropic", ("SOCRATES_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), 1_000_000),
    # Google Gemini
    "gemini-3.5-flash": ModelSpec("gemini/gemini-3.5-flash", "gemini", ("SOCRATES_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"), 1_000_000),
    "gemini-3.1-flash-lite": ModelSpec("gemini/gemini-3.1-flash-lite", "gemini", ("SOCRATES_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"), 1_000_000),
    "gemini-3.1-pro-preview": ModelSpec("gemini/gemini-3.1-pro-preview", "gemini", ("SOCRATES_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"), 1_000_000),
    # Moonshot Kimi
    "kimi-k2.6": ModelSpec("moonshot/kimi-k2.6", "moonshot", ("SOCRATES_MOONSHOT_API_KEY", "SOCRATES_KIMI_API_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY"), 256_000),
    "kimi-k2.5": ModelSpec("moonshot/kimi-k2.5", "moonshot", ("SOCRATES_MOONSHOT_API_KEY", "SOCRATES_KIMI_API_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY"), 256_000),
    # Zhipu / Z.ai
    "glm-5.1": ModelSpec("zai/glm-5.1", "zai", ("SOCRATES_ZAI_API_KEY", "SOCRATES_ZHIPU_API_KEY", "ZAI_API_KEY", "ZHIPU_API_KEY"), 200_000),
    "glm-5": ModelSpec("zai/glm-5", "zai", ("SOCRATES_ZAI_API_KEY", "SOCRATES_ZHIPU_API_KEY", "ZAI_API_KEY", "ZHIPU_API_KEY"), 200_000),
    "glm-4.7": ModelSpec("zai/glm-4.7", "zai", ("SOCRATES_ZAI_API_KEY", "SOCRATES_ZHIPU_API_KEY", "ZAI_API_KEY", "ZHIPU_API_KEY"), 200_000),
    "glm-4.6": ModelSpec("zai/glm-4.6", "zai", ("SOCRATES_ZAI_API_KEY", "SOCRATES_ZHIPU_API_KEY", "ZAI_API_KEY", "ZHIPU_API_KEY"), 200_000),
}


@dataclass
class Config:
    model_key: str = DEFAULT_MODEL
    model: str = ""
    api_base: str | None = None
    api_key: str | None = None
    max_tokens: int = 128_000
    compress_threshold: float = 0.7
    max_iterations: int = 50

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables."""
        config = cls()
        config.resolve_model(os.environ.get("SOCRATES_MODEL", DEFAULT_MODEL))
        return config

    def resolve_model(self, model_key: str | None) -> str:
        """Resolve a registry model key into runtime LiteLLM settings."""
        if not model_key:
            return self.model
        if model_key not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_key}")

        spec = MODEL_REGISTRY[model_key]
        self.model_key = model_key
        self.model = spec.litellm_model
        self.api_key = next((os.environ[key] for key in spec.env_keys if os.environ.get(key)), None)
        self.api_base = os.environ.get(f"SOCRATES_{spec.provider.upper()}_API_BASE") or spec.api_base
        self.max_tokens = spec.max_tokens
        return self.model
