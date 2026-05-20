"""Tool registry - all available tools for the agent."""

from socrates.tools.bash import BashTool
from socrates.tools.read_file import ReadFileTool
from socrates.tools.write_file import WriteFileTool
from socrates.tools.edit_file import EditFileTool
from socrates.tools.glob_tool import GlobTool
from socrates.tools.grep_tool import GrepTool

ALL_TOOLS = [
    BashTool(),
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    GlobTool(),
    GrepTool(),
]

TOOL_MAP = {tool.name: tool for tool in ALL_TOOLS}


def get_tool_schemas() -> list[dict]:
    """Get OpenAI-format tool schemas for all tools."""
    return [tool.to_schema() for tool in ALL_TOOLS]
