"""Bootstrap state helpers."""

from __future__ import annotations

from .state import (
    get_client_type,
    get_is_interactive,
    get_is_non_interactive_session,
    set_client_type,
    set_is_interactive,
)

__all__ = [
    "get_client_type",
    "get_is_interactive",
    "get_is_non_interactive_session",
    "set_client_type",
    "set_is_interactive",
]
