"""Create or overwrite a file."""

import os
from socrates.tools.base import BaseTool
from socrates.tools.edit_file import _changed_files


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Create a new file or completely overwrite an existing file. "
        "Use edit_file for partial modifications to existing files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to write to",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
            },
        },
        "required": ["file_path", "content"],
    }

    def execute(self, file_path: str, content: str, **kwargs) -> str:
        path = os.path.expanduser(file_path)
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            _changed_files.add(os.path.abspath(path))
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return f"Wrote {line_count} lines to {file_path}"
        except Exception as e:
            return f"[error] {e}"
