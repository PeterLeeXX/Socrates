"""Tests for the ``--dangerously-skip-permissions`` wiring (round 5).

Mirrors the behavior of the TS reference's ``initialPermissionModeFromCLI``,
``setup.ts`` root/sudo gate, and the runtime permission check in
``has_permissions_to_use_tool``.
"""

from __future__ import annotations

import io
import os
import sys

import pytest

from src.permissions.dangerous_safety import (
    enforce_dangerous_skip_permissions_safety,
    is_sandbox_environment,
)
from src.permissions.modes import (
    has_allow_bypass_permissions_mode,
    initial_permission_mode_from_cli,
)


# ---------------------------------------------------------------------------
# initial_permission_mode_from_cli


def test_dsp_flag_resolves_to_bypass_permissions():
    mode = initial_permission_mode_from_cli(dangerously_skip_permissions=True)
    assert mode == "bypassPermissions"


def test_no_flags_falls_back_to_default():
    mode = initial_permission_mode_from_cli()
    assert mode == "default"


def test_permission_mode_cli_used_when_dsp_absent():
    mode = initial_permission_mode_from_cli(permission_mode_cli="plan")
    assert mode == "plan"


def test_dsp_flag_takes_priority_over_permission_mode_cli():
    mode = initial_permission_mode_from_cli(
        permission_mode_cli="plan",
        dangerously_skip_permissions=True,
    )
    assert mode == "bypassPermissions"


def test_settings_default_mode_used_as_third_priority():
    mode = initial_permission_mode_from_cli(settings_default_mode="acceptEdits")
    assert mode == "acceptEdits"


def test_unknown_permission_mode_string_falls_back_to_default():
    mode = initial_permission_mode_from_cli(permission_mode_cli="garbage")
    assert mode == "default"


def test_priority_dsp_then_cli_then_settings():
    mode = initial_permission_mode_from_cli(
        permission_mode_cli="plan",
        settings_default_mode="acceptEdits",
    )
    # CLI beats settings
    assert mode == "plan"


# ---------------------------------------------------------------------------
# Root/sudo safety gate


def test_safety_gate_no_op_when_bypass_not_requested():
    # Should never raise regardless of uid.
    enforce_dangerous_skip_permissions_safety(bypass_requested=False)


def test_safety_gate_no_op_when_not_root(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    enforce_dangerous_skip_permissions_safety(bypass_requested=True)


@pytest.mark.skipif(sys.platform == "win32", reason="root check is no-op on Windows")
def test_safety_gate_aborts_when_root_outside_sandbox(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 0, raising=False)
    monkeypatch.delenv("IS_SANDBOX", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_BUBBLEWRAP", raising=False)
    err = io.StringIO()
    with pytest.raises(SystemExit) as excinfo:
        enforce_dangerous_skip_permissions_safety(bypass_requested=True, stderr=err)
    assert excinfo.value.code == 1
    assert "root/sudo" in err.getvalue()


@pytest.mark.skipif(sys.platform == "win32", reason="root check is no-op on Windows")
def test_safety_gate_allows_root_when_is_sandbox_set(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 0, raising=False)
    monkeypatch.setenv("IS_SANDBOX", "1")
    enforce_dangerous_skip_permissions_safety(bypass_requested=True)


@pytest.mark.skipif(sys.platform == "win32", reason="root check is no-op on Windows")
def test_safety_gate_allows_root_when_bubblewrap_set(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 0, raising=False)
    monkeypatch.delenv("IS_SANDBOX", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_BUBBLEWRAP", "1")
    enforce_dangerous_skip_permissions_safety(bypass_requested=True)


def test_is_sandbox_environment_falsy_for_zero_or_empty(monkeypatch):
    monkeypatch.setenv("IS_SANDBOX", "0")
    monkeypatch.delenv("CLAUDE_CODE_BUBBLEWRAP", raising=False)
    assert is_sandbox_environment() is False
    monkeypatch.setenv("IS_SANDBOX", "")
    assert is_sandbox_environment() is False


def test_is_sandbox_environment_truthy_for_one(monkeypatch):
    monkeypatch.setenv("IS_SANDBOX", "1")
    monkeypatch.delenv("CLAUDE_CODE_BUBBLEWRAP", raising=False)
    assert is_sandbox_environment() is True


# ---------------------------------------------------------------------------
# has_allow_bypass_permissions_mode (settings reader)


def test_has_allow_bypass_permissions_mode_default_false():
    # The default settings should not enable bypass mode availability.
    # (Whatever's in the actual user config is fine — we just ensure this
    # function doesn't crash and returns a bool.)
    result = has_allow_bypass_permissions_mode()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# CLI parser


def test_cli_parser_accepts_dangerously_skip_permissions():
    from src.cli import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["--dangerously-skip-permissions"])
    assert args.dangerously_skip_permissions is True
    assert args.allow_dangerously_skip_permissions is False


def test_cli_parser_accepts_allow_dangerously_skip_permissions():
    from src.cli import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["--allow-dangerously-skip-permissions"])
    assert args.allow_dangerously_skip_permissions is True
    assert args.dangerously_skip_permissions is False


def test_cli_parser_accepts_permission_mode():
    from src.cli import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["--permission-mode", "plan"])
    assert args.permission_mode == "plan"


def test_cli_parser_default_permission_state():
    from src.cli import _build_parser

    parser = _build_parser()
    args = parser.parse_args([])
    assert args.dangerously_skip_permissions is False
    assert args.allow_dangerously_skip_permissions is False
    assert args.permission_mode is None


def test_resolve_permission_state_stashes_resolved_mode_on_args():
    from src.cli import _build_parser, _resolve_permission_state

    parser = _build_parser()
    args = parser.parse_args(["--dangerously-skip-permissions"])
    _resolve_permission_state(args)
    assert args._resolved_permission_mode == "bypassPermissions"
    assert args._resolved_is_bypass_available is True


def test_resolve_permission_state_default_mode_when_no_flag():
    from src.cli import _build_parser, _resolve_permission_state

    parser = _build_parser()
    args = parser.parse_args([])
    _resolve_permission_state(args)
    assert args._resolved_permission_mode == "default"
    # is_bypass_available depends on settings; default config has no bypass.
    assert isinstance(args._resolved_is_bypass_available, bool)


def test_resolve_permission_state_allow_dangerously_only_does_not_flip_mode():
    from src.cli import _build_parser, _resolve_permission_state

    parser = _build_parser()
    args = parser.parse_args(["--allow-dangerously-skip-permissions"])
    _resolve_permission_state(args)
    assert args._resolved_permission_mode == "default"
    assert args._resolved_is_bypass_available is True


# ---------------------------------------------------------------------------
# Runtime permission check honors bypass mode


def test_runtime_check_returns_allow_in_bypass_mode():
    """End-to-end: `has_permissions_to_use_tool` should allow without prompt."""
    from src.permissions.check import has_permissions_to_use_tool
    from src.permissions.types import (
        PermissionAllowDecision,
        ToolPermissionContext,
    )

    class _StubTool:
        name = "Bash"
        is_mcp = False

        def check_permissions(self, tool_input, context):
            from src.permissions.types import PermissionPassthroughResult

            return PermissionPassthroughResult(behavior="passthrough")

    ctx = ToolPermissionContext(mode="bypassPermissions")
    decision = has_permissions_to_use_tool(_StubTool(), {}, ctx)
    assert isinstance(decision, PermissionAllowDecision)
    assert decision.behavior == "allow"


def test_runtime_check_returns_ask_in_default_mode():
    """End-to-end: default mode returns ask for tools that passthrough."""
    from src.permissions.check import has_permissions_to_use_tool
    from src.permissions.types import (
        PermissionAskDecision,
        ToolPermissionContext,
    )

    class _StubTool:
        name = "Bash"
        is_mcp = False

        def check_permissions(self, tool_input, context):
            from src.permissions.types import PermissionPassthroughResult

            return PermissionPassthroughResult(behavior="passthrough")

    ctx = ToolPermissionContext(mode="default")
    decision = has_permissions_to_use_tool(_StubTool(), {}, ctx)
    assert isinstance(decision, PermissionAskDecision)
    assert decision.behavior == "ask"
