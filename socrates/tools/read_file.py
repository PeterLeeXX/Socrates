"""Read file contents with optional line range."""

import os
from socrates.tools.base import BaseTool


def _is_binary(path: str) -> bool:
    """Quick check: if the first 512 bytes contain null bytes, it's binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(512)
        return b"\x00" in chunk
    except OSError:
        return False


class ReadFileTool(BaseTool):
    name = "read_file"
    description = (
        "Read the contents of a file. Returns line-numbered output. "
        "Use offset and limit to read specific portions of large files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read (relative or absolute)",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-based, default 0)",
                "default": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (default 2000)",
                "default": 2000,
            },
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, offset: int = 0, limit: int = 2000, **kwargs) -> str:
        path = os.path.expanduser(file_path)
        if not os.path.exists(path):
            return f"[error] File not found: {file_path}"
        if os.path.isdir(path):
            return f"[error] Path is a directory, not a file: {file_path}"
        if _is_binary(path):
            return f"[error] Binary file, not readable as text: {file_path}"

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"[error] {e}"

        total = len(lines)
        selected = lines[offset : offset + limit]

        result_lines = []
        for i, line in enumerate(selected, start=offset + 1):
            result_lines.append(f"{i:>6}\t{line.rstrip()}")

        header = f"[{total} lines total]"
        if offset > 0 or offset + limit < total:
            header += f" (showing lines {offset + 1}-{min(offset + limit, total)})"

        return header + "\n" + "\n".join(result_lines)
