"""Search file contents with regex."""

import os
import re
from pathlib import Path
from socrates.tools.base import BaseTool

# dirs that just add noise to search results
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"}


def _is_binary(path: str) -> bool:
    """Quick null-byte check."""
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(512)
    except OSError:
        return True


class GrepTool(BaseTool):
    name = "grep"
    description = (
        "Search for a regex pattern in file contents. "
        "Returns matching lines with file paths and line numbers."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (default: cwd)",
                "default": ".",
            },
            "include": {
                "type": "string",
                "description": "Glob pattern to filter files, e.g. '*.py' (default: all files)",
            },
        },
        "required": ["pattern"],
    }

    def execute(
        self, pattern: str, path: str = ".", include: str | None = None, **kwargs
    ) -> str:
        base = os.path.expanduser(path)

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"[error] Invalid regex: {e}"

        if not os.path.exists(base):
            return f"[error] Path not found: {path}"

        # single file
        if os.path.isfile(base):
            result = self._search_file(base, regex)
            return result if result else f"No matches for: {pattern}"

        # directory: walk and filter
        files = self._walk(Path(base), include)

        results = []
        match_count = 0
        for fpath in files:
            if match_count >= 500:
                results.append("\n... stopping at 500 matches")
                break
            file_result = self._search_file(str(fpath), regex)
            if file_result:
                results.append(file_result)
                match_count += file_result.count("\n") + 1

        if not results:
            return f"No matches for: {pattern}"
        return "\n\n".join(results)

    @staticmethod
    def _walk(root: Path, include: str | None) -> list[Path]:
        """Walk dir tree, skipping junk dirs and binary files."""
        results = []
        for item in root.rglob(include or "*"):
            if any(part in _SKIP_DIRS for part in item.parts):
                continue
            if item.is_file() and not _is_binary(str(item)):
                results.append(item)
            if len(results) >= 5000:
                break
        return sorted(results)

    @staticmethod
    def _search_file(fpath: str, regex) -> str | None:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (PermissionError, IsADirectoryError, OSError):
            return None

        matches = []
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                matches.append(f"  {i}: {line.rstrip()}")

        if not matches:
            return None
        return f"{fpath}\n" + "\n".join(matches)
