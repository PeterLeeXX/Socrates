"""REPL launcher."""

from __future__ import annotations

from pathlib import Path


def build_repl_banner() -> str:
    """One-line banner used by tests to confirm the module loads."""

    return "Socrates REPL (prompt_toolkit + Rich)."


def launch_repl(
    *,
    workspace_root: Path | None = None,
    stream: bool = True,
) -> int:
    """Boot the default interactive REPL.

    Args:
        workspace_root: Reserved; the REPL uses the current working directory.
        stream: Whether the REPL should enable live streaming.

    Returns:
        A conventional process exit code.
    """

    from src.cli import start_repl

    _ = workspace_root
    return start_repl(stream=stream)
