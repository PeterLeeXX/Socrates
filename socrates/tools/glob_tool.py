"""Find files by glob pattern."""

import os
import glob as globlib
from socrates.tools.base import BaseTool


class GlobTool(BaseTool):
    name = "glob"
    description = (
        "Find files matching a glob pattern. "
        "Supports patterns like '**/*.py', 'src/**/*.ts', '*.json'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files",
            },
            "path": {
                "type": "string",
                "description": "Base directory to search in (default: cwd)",
                "default": ".",
            },
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = ".", **kwargs) -> str:
        base = os.path.expanduser(path)
        full_pattern = os.path.join(base, pattern)

        try:
            matches = sorted(globlib.glob(full_pattern, recursive=True))
        except Exception as e:
            return f"[error] {e}"

        if not matches:
            return f"No files matched: {pattern}"

        # cap at 200 results to avoid flooding
        total = len(matches)
        shown = matches[:200]
        result = "\n".join(shown)
        if total > 200:
            result += f"\n\n... and {total - 200} more files"
        return f"[{total} matches]\n{result}"
