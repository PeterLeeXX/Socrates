"""Model system: resolution, capabilities, and validation."""

from __future__ import annotations

from .agent_routing import AgentModelConfig, get_model_for_agent
from .bedrock import (
    BEDROCK_MODEL_MAP,
    from_bedrock_model_id,
    to_bedrock_model_id,
)
from .capabilities import (
    get_model_capabilities,
    supports_computer_use,
    supports_thinking,
    supports_tools,
    supports_vision,
)
from .configs import MODEL_CONFIGS, ModelConfig, get_model_config
from .context import get_context_window_for_model, get_model_max_output_tokens
from .model import (
    canonical_model_name,
    display_name,
    resolve_model,
)
from .validation import is_model_allowed, validate_model_name

__all__ = [
    "BEDROCK_MODEL_MAP",
    "MODEL_CONFIGS",
    "AgentModelConfig",
    "ModelConfig",
    "canonical_model_name",
    "display_name",
    "from_bedrock_model_id",
    "get_context_window_for_model",
    "get_model_capabilities",
    "get_model_config",
    "get_model_for_agent",
    "get_model_max_output_tokens",
    "is_model_allowed",
    "resolve_model",
    "supports_computer_use",
    "supports_thinking",
    "supports_tools",
    "supports_vision",
    "to_bedrock_model_id",
    "validate_model_name",
]
