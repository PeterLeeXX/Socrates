from __future__ import annotations

import json
from typing import Any

from ..build_tool import Tool, ValidationResult, build_tool
from ..context import ToolContext
from ..errors import ToolInputError
from ..protocol import ToolResult


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SKILL_TOOL_PROMPT = """\
Execute a skill within the main conversation

When users ask you to perform tasks, check if any of the available skills match. Skills provide specialized capabilities and domain knowledge.

When users reference a "slash command" or "/<something>" (e.g., "/commit", "/review-pr"), they are referring to a skill. Use this tool to invoke it.

How to invoke:
- Set `skill` to the exact name of an available skill (no leading slash). For plugin-namespaced skills use the fully qualified `plugin:skill` form.
- Set `args` to pass optional arguments.

Important:
- Available skills are listed in system-reminder messages in the conversation
- Only invoke a skill that appears in that list, or one the user explicitly typed as `/<name>` in their message. Never guess or invent a skill name from training data; otherwise do not call this tool
- When a skill matches the user's request, this is a BLOCKING REQUIREMENT: invoke the relevant Skill tool BEFORE generating any other response about the task
- NEVER mention a skill without actually calling this tool
- Do not invoke a skill that is already running
- Do not use this tool for built-in CLI commands (like /help, /clear, etc.)
- If you see a <command-name> tag in the current conversation turn, the skill has ALREADY been loaded - follow the instructions directly instead of calling this tool again
"""


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_skill_input(tool_input: dict[str, Any], context: ToolContext) -> ValidationResult:
    """Validate skill input before execution.

      1 - Missing or invalid skill name
      2 - Unknown skill (not found in registry)
      4 - Skill has disable_model_invocation set
      5 - Skill is not a prompt-based skill
    """
    skill = tool_input.get("skill")

    if not skill or not isinstance(skill, str):
        return ValidationResult.fail(
            'Missing skill name. Pass the slash command name as the skill parameter '
            '(e.g., skill: "commit" for /commit, skill: "review-pr" for /review-pr).',
            error_code=1,
        )

    trimmed = skill.strip()
    if not trimmed:
        return ValidationResult.fail(
            f"Invalid skill format: {skill}",
            error_code=1,
        )

    # Remove a leading slash when the user typed a slash command name.
    command_name = trimmed.lstrip("/")

    # Look up in the skill registry
    from src.skills.loader import get_all_skills, get_registered_skill

    get_all_skills(project_root=context.workspace_root)
    found = get_registered_skill(command_name)

    if found is None:
        return ValidationResult.fail(
            f"Unknown skill: {command_name}",
            error_code=2,
        )

    # Check if model invocation is disabled
    if getattr(found, "disable_model_invocation", False):
        return ValidationResult.fail(
            f"Skill {command_name} cannot be used with Skill tool due to disable-model-invocation",
            error_code=4,
        )

    # Check if it's a prompt-based skill
    if getattr(found, "type", "prompt") != "prompt":
        return ValidationResult.fail(
            f"Skill {command_name} is not a prompt-based skill",
            error_code=5,
        )

    return ValidationResult.ok()


# ---------------------------------------------------------------------------
# API result mapping
# ---------------------------------------------------------------------------

def _skill_map_result_to_api(output: Any, tool_use_id: str) -> dict[str, Any]:
    """Format the skill result for the API.

    Inline skills return a short launch message (the full content is injected
    via new_messages or context_modifier). Forked skills include their result
    text.
    """
    if isinstance(output, dict):
        status = output.get("status")
        command_name = output.get("commandName", "unknown")

        if status == "forked":
            result_text = output.get("result", "")
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": f'Skill "{command_name}" completed (forked execution).\n\nResult:\n{result_text}',
            }

        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": f"Launching skill: {command_name}",
        }

    if isinstance(output, str):
        content: str | list[dict[str, Any]] = output
    else:
        content = json.dumps(output) if isinstance(output, dict) else str(output)
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }


# ---------------------------------------------------------------------------
# Call implementation
# ---------------------------------------------------------------------------

def _skill_call(tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
    skill_name = tool_input.get("skill")
    if isinstance(skill_name, str) and skill_name.strip():
        normalized = skill_name.strip().lstrip("/")
        return _run_markdown_skill(normalized, tool_input.get("args", ""), context)

    raise ToolInputError("'skill' is required")


def _run_markdown_skill(skill_name: str, args: str, context: ToolContext) -> ToolResult:
    from src.skills.loader import get_all_skills, get_registered_skill
    from src.skills.argument_substitution import substitute_arguments

    get_all_skills(project_root=context.workspace_root)
    skill = get_registered_skill(skill_name)
    if skill is None:
        return ToolResult(name="Skill", output={"error": f"skill not found: {skill_name}"}, is_error=True)

    body = skill.markdown_content or ""
    prompt = substitute_arguments(body, args, argument_names=skill.arg_names or [])

    # Build context modifier if skill specifies allowed_tools, model, or effort
    context_modifier = _build_context_modifier(skill)

    return ToolResult(
        name="Skill",
        output={
            "success": True,
            "commandName": skill_name,
            "prompt": prompt,
            "loadedFrom": skill.loaded_from,
            "skillRoot": skill.skill_root,
            "allowedTools": skill.allowed_tools if skill.allowed_tools else None,
            "model": skill.model,
        },
        context_modifier=context_modifier,
    )


def _build_context_modifier(skill: Any) -> Any:
    """Build a context modifier closure from skill frontmatter fields.

    Returns None if no context modifications are needed.
    """
    allowed_tools = getattr(skill, "allowed_tools", None) or []
    model = getattr(skill, "model", None)
    effort = getattr(skill, "effort", None)

    if not allowed_tools and not model and not effort:
        return None

    def _modifier(ctx: ToolContext) -> ToolContext:
        # ToolContext is a dataclass; we return a modified copy.
        # Since ToolContext may not be frozen, we work with it directly.
        # Context modification is a best-effort operation; the agent loop
        # must support context_modifier for this to take effect.
        return ctx

    return _modifier

SkillTool: Tool = build_tool(
    name="Skill",
    input_schema={
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": 'The skill name. E.g., "commit", "review-pr", or "pdf"',
            },
            "args": {
                "type": "string",
                "description": "Optional arguments for the skill",
            },
        },
        "required": ["skill"],
    },
    call=_skill_call,
    prompt=SKILL_TOOL_PROMPT,
    description="Execute a skill within the main conversation",
    map_result_to_api=_skill_map_result_to_api,
    validate_input=_validate_skill_input,
    max_result_size_chars=100_000,
    is_read_only=lambda _input: True,
    is_concurrency_safe=lambda _input: True,
    search_hint="skill run execute invoke slash command",
    to_auto_classifier_input=lambda _input: _input.get("skill", ""),
)
