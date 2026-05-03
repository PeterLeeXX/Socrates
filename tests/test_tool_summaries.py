from __future__ import annotations

from src.tool_system.tool_summaries import summarize_tool_use


def test_summarize_tool_use_for_file_tools() -> None:
    assert summarize_tool_use("Read", {"file_path": "src/app.py"}) == "src/app.py"
    assert summarize_tool_use("Write", {"filePath": "out.txt"}) == "out.txt"
    assert summarize_tool_use("Edit", {"path": "main.py"}) == "main.py"


def test_summarize_tool_use_for_search_tools() -> None:
    assert summarize_tool_use("Glob", {"pattern": "*.py", "path": "src"}) == "*.py 路 src"
    assert summarize_tool_use("Grep", {"pattern": "needle"}) == "needle"


def test_summarize_tool_use_for_bash_truncates_long_command() -> None:
    command = "x" * 100
    summary = summarize_tool_use("Bash", {"command": command})

    assert summary == ("x" * 77) + "..."
