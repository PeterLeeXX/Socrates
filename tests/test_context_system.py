from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.context_system import build_context_prompt
from src.context_system.claude_md import clear_memory_file_caches
from src.context_system.git_context import clear_git_caches, collect_git_context


def _run(coro):
    return asyncio.run(coro)


class TestContextSystem(unittest.TestCase):
    def setUp(self):
        clear_memory_file_caches()
        clear_git_caches()

    def tearDown(self):
        clear_memory_file_caches()
        clear_git_caches()

    def test_build_context_prompt_includes_workspace_and_claude_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text("Project rule: always add tests.", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

            with patch.dict(os.environ, {"CLAUDE_CODE_ORIGINAL_CWD": tmp}):
                prompt = build_context_prompt(root)

            self.assertIn("## Runtime Context", prompt)
            self.assertIn("## Project Instructions", prompt)
            self.assertIn("Project rule: always add tests.", prompt)
            self.assertIn("README.md", prompt)
            self.assertIn("pyproject.toml", prompt)

    def test_collect_git_context_handles_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _run(collect_git_context(tmp))
            self.assertFalse(ctx.available)

if __name__ == "__main__":
    unittest.main()
