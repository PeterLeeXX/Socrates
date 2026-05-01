"""DeepSeek provider implementation.

DeepSeek exposes an OpenAI-compatible API at https://api.deepseek.com.
Current production models are ``deepseek-v4-pro`` and ``deepseek-v4-flash``.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from openai import OpenAI  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    OpenAI = None

from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider using the OpenAI SDK against the DeepSeek base URL."""

    DEFAULT_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None
    ):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key (sk-...)
            base_url: Base URL (optional, defaults to https://api.deepseek.com)
            model: Default model (default: deepseek-v4-pro)
        """
        super().__init__(
            api_key,
            base_url or self.DEFAULT_BASE_URL,
            model or "deepseek-v4-pro",
        )

    def _create_client(self) -> Any:
        """Create OpenAI SDK client pointed at DeepSeek."""
        if OpenAI is None:  # pragma: no cover
            raise ModuleNotFoundError(
                "openai package is not installed. Install optional dependencies to use DeepSeekProvider."
            )
        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "base_url": self.base_url or self.DEFAULT_BASE_URL,
        }
        import os
        if os.environ.get("SOCRATES_SSL_VERIFY", "").lower() in ("0", "false", "no"):
            import httpx
            kwargs["http_client"] = httpx.Client(verify=False)
        return OpenAI(**kwargs)

    def get_available_models(self) -> list[str]:
        """Return DeepSeek's current production models."""
        return [
            "deepseek-v4-pro",
            "deepseek-v4-flash",
        ]
