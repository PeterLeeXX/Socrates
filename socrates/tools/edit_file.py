"""Search-and-replace editing with diff output."""

import difflib
import os
from socrates.tools.base import BaseTool

# track which files got modified this session
_changed_files: set[str] = set()


def _unified_diff(old: str, new: str, filename: str, context: int = 3) -> str:
    """Generate a compact unified diff."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}", tofile=f"b/{filename}",
        n=context,
    )
    result = "".join(diff)
    if len(result) > 3000:
        result = result[:2500] + "\n... (diff truncated)\n"
    return result


class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Make targeted edits to a file by replacing exact string matches. "
        "The old_string must appear exactly once in the file (unless replace_all is true). "
        "Prefer this over write_file for modifying existing files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "Exact text to search for",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement text",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences instead of just one (default false)",
                "default": False,
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    def execute(
        self, file_path: str, old_string: str, new_string: str,
        replace_all: bool = False, **kwargs
    ) -> str:
        path = os.path.expanduser(file_path)
        if not os.path.exists(path):
            return f"[error] File not found: {file_path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[error] {e}"

        count = content.count(old_string)
        if count == 0:
            return (
                f"[error] old_string not found in {file_path}. "
                "Make sure the string matches exactly, including whitespace and indentation."
            )

        if not replace_all and count > 1:
            return (
                f"[error] old_string appears {count} times in {file_path}. "
                "Provide more surrounding context to make it unique, "
                "or set replace_all=true to replace all occurrences."
            )

        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            return f"[error] {e}"

        _changed_files.add(os.path.abspath(path))
        diff = _unified_diff(content, new_content, file_path)
        return f"Edited {file_path}\n{diff}"
