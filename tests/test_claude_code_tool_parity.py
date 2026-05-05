from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from src.tool_system.context import ToolContext
from src.tool_system.defaults import build_default_registry
from src.tool_system.protocol import ToolCall


class TestClaudeCodeToolParity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.registry = build_default_registry(include_user_tools=False)
        self.ctx = ToolContext(workspace_root=self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_registry_has_claude_code_tool_names(self) -> None:
        expected = [
            "Agent",
            "AskUserQuestion",
            "Bash",
            "Config",
            "CronCreate",
            "CronDelete",
            "CronList",
            "Edit",
            "EnterPlanMode",
            "EnterWorktree",
            "ExitPlanMode",
            "ExitWorktree",
            "Glob",
            "Grep",
            "LSP",
            "ListMcpResourcesTool",
            "MCP",
            "NotebookEdit",
            "PowerShell",
            "REPL",
            "Read",
            "ReadMcpResourceTool",
            "RemoteTrigger",
            "SendMessage",
            "SendUserMessage",
            "Skill",
            "Sleep",
            "StructuredOutput",
            "TaskCreate",
            "TaskGet",
            "TaskList",
            "TaskOutput",
            "TaskStop",
            "TaskUpdate",
            "ToolSearch",
            "WebFetch",
            "WebSearch",
            "Write",
        ]
        not_yet_implemented = {"NotebookEdit", "PowerShell", "REPL", "RemoteTrigger", "SendMessage"}
        missing = [name for name in expected if self.registry.get(name) is None and name not in not_yet_implemented]
        self.assertEqual(missing, [])

    def test_tool_search_select(self) -> None:
        out = self.registry.dispatch(
            ToolCall(name="ToolSearch", input={"query": "select:Read"}),
            self.ctx,
        ).output
        self.assertEqual(out["matches"], ["Read"])

if __name__ == "__main__":
    unittest.main()
