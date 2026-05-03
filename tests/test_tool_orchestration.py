"""Tests for tool orchestration — partition_tool_calls and batch execution."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.tool_execution.orchestrator import (
    Batch,
    partition_tool_calls,
)
from src.services.tool_execution.tool_execution import run_tool_use
from src.services.tool_execution.streaming_executor import ToolUseBlock
from src.tool_system.build_tool import build_tool, Tool
from src.tool_system.context import ToolContext, ToolUseOptions
from src.tool_system.protocol import ToolResult
from src.types.content_blocks import ToolResultBlock
from src.types.messages import AssistantMessage


def _make_tool(name: str, concurrency_safe: bool = False) -> Tool:
    return build_tool(
        name=name,
        input_schema={"type": "object", "properties": {}},
        call=lambda inp, ctx: ToolResult(name=name, output="ok"),
        is_concurrency_safe=lambda _inp: concurrency_safe,
    )


def _make_context(tools: list[Tool]) -> ToolContext:
    return ToolContext(
        workspace_root=Path("/tmp"),
        options=ToolUseOptions(tools=tools),
    )


def _make_block(name: str, tool_id: str = "tu_1") -> ToolUseBlock:
    return ToolUseBlock(id=tool_id, name=name, input={})


class TestPartitionToolCalls:
    def test_single_non_concurrent(self):
        tools = [_make_tool("A", False)]
        ctx = _make_context(tools)
        blocks = [_make_block("A", "1")]
        batches = partition_tool_calls(blocks, ctx)
        assert len(batches) == 1
        assert not batches[0].is_concurrency_safe
        assert len(batches[0].blocks) == 1

    def test_consecutive_concurrent_batched(self):
        tools = [_make_tool("A", True)]
        ctx = _make_context(tools)
        blocks = [
            _make_block("A", "1"),
            _make_block("A", "2"),
            _make_block("A", "3"),
        ]
        batches = partition_tool_calls(blocks, ctx)
        assert len(batches) == 1
        assert batches[0].is_concurrency_safe
        assert len(batches[0].blocks) == 3

    def test_mixed_partitioning(self):
        tool_a = _make_tool("A", True)
        tool_b = _make_tool("B", False)
        ctx = _make_context([tool_a, tool_b])
        blocks = [
            _make_block("A", "1"),
            _make_block("A", "2"),
            _make_block("B", "3"),
            _make_block("A", "4"),
        ]
        batches = partition_tool_calls(blocks, ctx)
        assert len(batches) == 3
        assert batches[0].is_concurrency_safe
        assert len(batches[0].blocks) == 2
        assert not batches[1].is_concurrency_safe
        assert len(batches[1].blocks) == 1
        assert batches[2].is_concurrency_safe
        assert len(batches[2].blocks) == 1

    def test_unknown_tool_not_concurrent(self):
        ctx = _make_context([])
        blocks = [_make_block("Unknown", "1")]
        batches = partition_tool_calls(blocks, ctx)
        assert len(batches) == 1
        assert not batches[0].is_concurrency_safe

    def test_empty_list(self):
        ctx = _make_context([])
        batches = partition_tool_calls([], ctx)
        assert len(batches) == 0


class TestToolExecutionEventLoopBoundary:
    @pytest.mark.asyncio
    async def test_sync_tool_can_bridge_to_async_from_running_loop(self):
        """Sync tools that own async bridges should not run inside query loop."""

        async def _inner() -> str:
            return "ok"

        def _call(_inp, _ctx):
            return ToolResult(name="NestedAsync", output=asyncio.run(_inner()))

        tool = build_tool(
            name="NestedAsync",
            input_schema={"type": "object", "properties": {}},
            call=_call,
        )
        ctx = _make_context([tool])
        block = ToolUseBlock(id="tu_nested", name="NestedAsync", input={})
        assistant = AssistantMessage(content=[block])

        updates = [
            update
            async for update in run_tool_use(block, assistant, None, ctx)
        ]

        assert len(updates) == 1
        msg = updates[0].message
        assert msg is not None
        assert isinstance(msg.content, list)
        result = msg.content[0]
        assert isinstance(result, ToolResultBlock)
        assert result.content == "ok"
        assert result.is_error is False
