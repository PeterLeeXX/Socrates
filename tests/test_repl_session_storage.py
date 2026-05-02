from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.repl import SocratesREPL
from src.services.session_resume import resume_session
from src.types.content_blocks import ToolResultBlock
from src.types.messages import AssistantMessage, UserMessage


class _FakeQueryEngine:
    last_instance: "_FakeQueryEngine | None" = None

    def __init__(self, config):
        self._messages = list(config.initial_messages or [])
        self._interrupted = False
        _FakeQueryEngine.last_instance = self

    async def submit_message(self, prompt: str):
        self._messages.append(UserMessage(content=prompt))
        assistant = AssistantMessage(content="Working")
        self._messages.append(assistant)
        yield assistant

        tool_result = UserMessage(
            content=[ToolResultBlock(tool_use_id="tu_1", content="tool output")]
        )
        self._messages.append(tool_result)
        yield tool_result

    def get_messages(self):
        return list(self._messages)

    def interrupt(self):
        self._interrupted = True

    def reset_abort_controller(self):
        pass


class TestREPLSessionStorage(unittest.TestCase):
    def _new_repl(self, sessions_dir: Path) -> SocratesREPL:
        provider = Mock()
        provider.model = "glm-4.5"

        config = {
            "api_key": "test-key",
            "base_url": "https://example.test",
            "default_model": "glm-4.5",
        }

        with patch("src.repl.core.get_provider_config", return_value=config):
            with patch("src.repl.core.get_provider_class", return_value=Mock(return_value=provider)):
                repl = SocratesREPL(provider_name="glm", sessions_dir=sessions_dir)
                repl.console = Mock()
                return repl

    def test_chat_auto_persists_turn_and_resume_restores_messages(self):
        with tempfile.TemporaryDirectory() as td:
            sessions_dir = Path(td)
            repl = self._new_repl(sessions_dir)

            with patch("src.repl.core.QueryEngine", _FakeQueryEngine):
                repl.chat("hello")

            result = resume_session(repl.session_id, sessions_dir=sessions_dir)

            self.assertTrue(result.success)
            self.assertEqual([m.role for m in result.messages], ["user", "assistant", "user"])
            self.assertEqual(result.messages[0].content, "hello")
            self.assertEqual(result.metadata.model, "glm-4.5")
            self.assertEqual(result.metadata.cwd, str(Path.cwd()))
            self.assertEqual(result.metadata.message_count, 3)

    def test_save_command_is_not_registered(self):
        with tempfile.TemporaryDirectory() as td:
            repl = self._new_repl(Path(td))

            self.assertNotIn("/save", repl._built_in_commands)
            self.assertNotIn("/save", repl._original_built_ins)


if __name__ == "__main__":
    unittest.main()
