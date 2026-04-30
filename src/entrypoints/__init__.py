"""Runtime entrypoints for headless mode."""

from __future__ import annotations

from .headless import HeadlessOptions, run_headless

__all__ = [
    "HeadlessOptions",
    "run_headless",
]
