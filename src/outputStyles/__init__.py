"""Output style loading and built-in style definitions."""

from __future__ import annotations

from .loader import load_output_styles_dir, resolve_output_style
from .styles import BUILTIN_OUTPUT_STYLES, OutputStyle

__all__ = [
    "BUILTIN_OUTPUT_STYLES",
    "OutputStyle",
    "load_output_styles_dir",
    "resolve_output_style",
]
