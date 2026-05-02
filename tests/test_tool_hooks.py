"""Tests for tool hooks (pre/post tool use)."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.services.tool_execution.tool_hooks import resolve_hook_permission_decision
from src.services.tool_execution.tool_execution import run_tool_use
from src.services.tool_execution.streaming_executor import ToolUseBlock
from src.tool_system.build_tool import build_tool, Tool
from src.tool_system.context import ToolContext, ToolUseOptions
from src.tool_system.protocol import ToolResult
from src.types.content_blocks import ToolResultBlock
from src.types.messages import AssistantMessage, create_assistant_message


def _make_tool(name: str = "TestTool") -> Tool:
    return build_tool(
        name=name,
        input_schema={"type": "object", "properties": {}},
        call=lambda inp, ctx: ToolResult(name=name, output="ok"),
    )


def _make_context() -> ToolContext:
    return ToolContext(
        workspace_root=Path("/tmp"),
        options=ToolUseOptions(),
    )


def _make_assistant_msg() -> AssistantMessage:
    return create_assistant_message(content="test")


class TestResolveHookPermissionDecision:
    @pytest.mark.asyncio
    async def test_no_hook_result_no_can_use_tool(self):
        tool = _make_tool()
        ctx = _make_context()
        decision = await resolve_hook_permission_decision(
            None, tool, {}, ctx, None, _make_assistant_msg(), "tu_1"
        )
        assert decision["behavior"] == "allow"

    @pytest.mark.asyncio
    async def test_hook_allow(self):
        tool = _make_tool()
        ctx = _make_context()
        hook_result = {"behavior": "allow"}
        decision = await resolve_hook_permission_decision(
            hook_result, tool, {}, ctx, None, _make_assistant_msg(), "tu_1"
        )
        assert decision["behavior"] == "allow"

    @pytest.mark.asyncio
    async def test_hook_deny(self):
        tool = _make_tool()
        ctx = _make_context()
        hook_result = {"behavior": "deny", "message": "blocked"}
        decision = await resolve_hook_permission_decision(
            hook_result, tool, {}, ctx, None, _make_assistant_msg(), "tu_1"
        )
        assert decision["behavior"] == "deny"
        assert decision["message"] == "blocked"

    @pytest.mark.asyncio
    async def test_hook_allow_with_updated_input(self):
        tool = _make_tool()
        ctx = _make_context()
        hook_result = {
            "behavior": "allow",
            "updatedInput": {"key": "new_value"},
        }
        decision = await resolve_hook_permission_decision(
            hook_result, tool, {"key": "old_value"}, ctx, None, _make_assistant_msg(), "tu_1"
        )
        assert decision["behavior"] == "allow"
        assert decision.get("input", {}).get("key") == "new_value"

    @pytest.mark.asyncio
    async def test_can_use_tool_called_when_no_hook(self):
        tool = _make_tool()
        ctx = _make_context()
        called = []

        async def mock_can_use_tool(t, inp, ctx, msg, tuid, force=None):
            called.append(True)
            return {"behavior": "allow"}

        decision = await resolve_hook_permission_decision(
            None, tool, {}, ctx, mock_can_use_tool, _make_assistant_msg(), "tu_1"
        )
        assert len(called) == 1
        assert decision["behavior"] == "allow"

    @pytest.mark.asyncio
    async def test_hook_ask_passes_to_can_use_tool(self):
        tool = _make_tool()
        ctx = _make_context()

        async def mock_can_use_tool(t, inp, ctx, msg, tuid, force=None):
            return {"behavior": "allow", "userModified": True}

        hook_result = {"behavior": "ask", "message": "Please approve"}
        decision = await resolve_hook_permission_decision(
            hook_result, tool, {}, ctx, mock_can_use_tool, _make_assistant_msg(), "tu_1"
        )
        assert decision["behavior"] == "allow"


class TestRunToolUsePermissionInput:
    @pytest.mark.asyncio
    async def test_permission_decision_input_replaces_tool_input(self):
        tool = build_tool(
            name="EchoInput",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            call=lambda inp, ctx: ToolResult(name="EchoInput", output={"value": inp["value"]}),
        )
        ctx = ToolContext(
            workspace_root=Path("/tmp"),
            options=ToolUseOptions(tools=[tool]),
        )

        async def can_use_tool(_tool, _inp, _ctx, _msg, _tool_use_id):
            return {"behavior": "allow", "input": {"value": "from-permission"}}

        messages = []
        async for update in run_tool_use(
            ToolUseBlock(id="tu_1", name="EchoInput", input={"value": "original"}),
            _make_assistant_msg(),
            can_use_tool,
            ctx,
        ):
            if update.message is not None:
                messages.append(update.message)

        content = ""
        for msg in messages:
            for block in msg.content:
                if isinstance(block, ToolResultBlock):
                    content += block.content

        assert "from-permission" in content
        assert "original" not in content
