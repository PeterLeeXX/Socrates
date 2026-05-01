"""Model name helpers."""

from __future__ import annotations

from .configs import get_model_config


def resolve_model(name: str) -> str:
    """Return the model name selected by the caller."""
    return name


def canonical_model_name(name: str) -> str:
    """Get the canonical model name."""
    return resolve_model(name)


def display_name(model_id: str) -> str:
    """Get a human-readable display name for a model."""
    config = get_model_config(model_id)
    if config:
        return config.display_name
    return model_id.replace("-", " ").title()
