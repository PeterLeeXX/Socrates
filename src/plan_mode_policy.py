from __future__ import annotations

from typing import Any


PLAN_MODE_ALLOWED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "AskUserQuestion",
        "EnterPlanMode",
        "ExitPlanMode",
        "Glob",
        "Grep",
        "LSP",
        "ListMcpResources",
        "Read",
        "ReadMcpResource",
        "Status",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskUpdate",
        "WebFetch",
        "WebSearch",
    }
)

PLAN_MODE_RESTRICTED_TOOL_NAMES: tuple[str, ...] = (
    "Agent",
    "Bash",
    "ClipboardWrite",
    "Config",
    "CronCreate",
    "CronDelete",
    "Edit",
    "MCP",
    "NotebookEdit",
    "StructuredOutput",
    "TeamCreate",
    "TeamDelete",
    "Write",
)


def is_tool_allowed_in_plan_mode(tool: Any) -> bool:
    name = getattr(tool, "name", "")
    return name in PLAN_MODE_ALLOWED_TOOL_NAMES


def filter_tools_for_plan_mode(tools: list[Any]) -> list[Any]:
    return [tool for tool in tools if is_tool_allowed_in_plan_mode(tool)]
