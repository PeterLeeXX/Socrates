import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.providers.base import ChatResponse
from src.permissions.check import has_permissions_to_use_tool
from src.permissions.types import PermissionDenyDecision
from src.tool_system.context import ToolContext
from src.tool_system.defaults import build_default_registry
from src.types.content_blocks import TextBlock
from src.types.messages import AssistantMessage, UserMessage
from src.utils.abort_controller import AbortController

from src.query.engine import QueryEngine, QueryEngineConfig
from src.query.query import StreamEvent


def _run(coro):
    return asyncio.run(coro)


class TestQueryEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.registry = build_default_registry()
        self.context = ToolContext(workspace_root=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_engine(self, provider) -> QueryEngine:
        tools = self.registry.list_tools()
        config = QueryEngineConfig(
            cwd=self.workspace,
            provider=provider,
            tool_registry=self.registry,
            tools=tools,
            tool_context=self.context,
            system_prompt="You are helpful.",
            max_turns=10,
        )
        return QueryEngine(config)

    def test_submit_message_yields_assistant(self):
        provider = MagicMock()
        provider.chat_stream_response.side_effect = NotImplementedError()
        provider.chat.return_value = ChatResponse(
            content="Test response",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 5},
            finish_reason="end_turn",
            tool_uses=None,
        )

        engine = self._make_engine(provider)
        collected = []

        async def run():
            async for msg in engine.submit_message("Hello"):
                collected.append(msg)

        _run(run())

        assistants = [m for m in collected if isinstance(m, AssistantMessage)]
        self.assertEqual(len(assistants), 1)

    def test_messages_accumulate(self):
        provider = MagicMock()
        provider.chat_stream_response.side_effect = NotImplementedError()
        provider.chat.return_value = ChatResponse(
            content="Response",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 5},
            finish_reason="end_turn",
            tool_uses=None,
        )

        engine = self._make_engine(provider)

        async def run():
            async for _ in engine.submit_message("First"):
                pass

        _run(run())

        msgs = engine.get_messages()
        user_msgs = [m for m in msgs if isinstance(m, UserMessage)]
        assistant_msgs = [m for m in msgs if isinstance(m, AssistantMessage)]
        self.assertGreaterEqual(len(user_msgs), 1)
        self.assertGreaterEqual(len(assistant_msgs), 1)

    def test_interrupt(self):
        engine = self._make_engine(MagicMock())
        engine.interrupt()

    def test_reset_abort_controller(self):
        provider = MagicMock()
        provider.chat_stream_response.side_effect = NotImplementedError()
        provider.chat.return_value = ChatResponse(
            content="Response",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 5},
            finish_reason="end_turn",
            tool_uses=None,
        )

        engine = self._make_engine(provider)
        engine.interrupt()
        engine.reset_abort_controller()

        collected = []

        async def run():
            async for msg in engine.submit_message("Hello again"):
                collected.append(msg)

        _run(run())

        assistants = [m for m in collected if isinstance(m, AssistantMessage)]
        self.assertGreaterEqual(len(assistants), 1)

    def test_session_id_exists(self):
        engine = self._make_engine(MagicMock())
        self.assertIsInstance(engine.session_id, str)
        self.assertGreater(len(engine.session_id), 0)

    def test_plan_mode_injects_prompt_and_defers_tool_filtering_to_query_loop(self):
        provider = MagicMock()
        self.context.plan_mode = True

        captured = {}

        async def fake_query(params):
            captured["system_prompt"] = params.system_prompt
            captured["tools"] = [tool.name for tool in params.tools]
            yield AssistantMessage(content="planned")

        config = QueryEngineConfig(
            cwd=self.workspace,
            provider=provider,
            tool_registry=self.registry,
            tools=self.registry.list_tools(),
            tool_context=self.context,
            max_turns=10,
        )
        engine = QueryEngine(config)

        async def run():
            with unittest.mock.patch("src.query.engine.query", fake_query):
                async for _ in engine.submit_message("Plan a change"):
                    pass

        _run(run())

        self.assertIn("PLAN MODE", captured["system_prompt"])
        self.assertIn("NOT available", captured["system_prompt"])
        self.assertIn("Write", captured["system_prompt"])
        self.assertIn("Bash", captured["system_prompt"])
        self.assertIn("Read", captured["tools"])
        self.assertIn("ExitPlanMode", captured["tools"])
        self.assertIn("Write", captured["tools"])
        self.assertIn("Edit", captured["tools"])
        self.assertIn("Bash", captured["tools"])

    def test_plan_mode_permission_guard_denies_write_but_allows_exit(self):
        self.context.plan_mode = True
        write_tool = self.registry.get("Write")
        exit_tool = self.registry.get("ExitPlanMode")

        write_decision = has_permissions_to_use_tool(
            write_tool,
            {},
            self.context.permission_context,
            tool_use_context=self.context,
        )
        exit_decision = has_permissions_to_use_tool(
            exit_tool,
            {},
            self.context.permission_context,
            tool_use_context=self.context,
        )

        self.assertIsInstance(write_decision, PermissionDenyDecision)
        self.assertIn("plan mode", write_decision.message)
        self.assertNotEqual(exit_decision.behavior, "deny")


if __name__ == "__main__":
    unittest.main()
