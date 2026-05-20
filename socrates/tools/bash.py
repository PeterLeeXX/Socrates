"""Execute shell commands with safety checks and cd tracking."""

import os
import re
import subprocess
import threading
from socrates.tools.base import BaseTool

# track cwd across commands so `cd src && ls` works as expected
_cwd: str | None = None
_cwd_lock = threading.Lock()

# patterns that could wreck the filesystem or leak secrets
_DANGEROUS_PATTERNS = [
    (r"\brm\s+(-\w*)?-r\w*\s+(/|~|\$HOME)", "recursive delete on home/root"),
    (r"\brm\s+(-\w*)?-rf\s", "force recursive delete"),
    (r"\bmkfs\b", "format filesystem"),
    (r"\bdd\s+.*of=/dev/", "raw disk write"),
    (r">\s*/dev/sd[a-z]", "overwrite block device"),
    (r"\bchmod\s+(-R\s+)?777\s+/", "chmod 777 on root"),
    (r":\(\)\s*\{.*:\|:.*\}", "fork bomb"),
    (r"\bcurl\b.*\|\s*(sudo\s+)?bash", "pipe curl to bash"),
    (r"\bwget\b.*\|\s*(sudo\s+)?bash", "pipe wget to bash"),
]


def _check_dangerous(cmd: str) -> str | None:
    """Return a warning string if the command looks destructive."""
    for pattern, reason in _DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return reason
    return None


def _update_cwd(command: str, current_cwd: str):
    """Track directory changes from cd commands."""
    global _cwd
    for part in command.split("&&"):
        part = part.strip()
        if part.startswith("cd "):
            target = part[3:].strip().strip("'\"")
            if target:
                new_dir = os.path.normpath(os.path.join(current_cwd, os.path.expanduser(target)))
                if os.path.isdir(new_dir):
                    with _cwd_lock:
                        _cwd = new_dir


class BashTool(BaseTool):
    name = "bash"
    description = (
        "Execute a shell command and return its output. "
        "Use for running tests, installing packages, git operations, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 120)",
                "default": 120,
            },
        },
        "required": ["command"],
    }

    def execute(self, command: str, timeout: int = 120, **kwargs) -> str:
        # safety check
        warning = _check_dangerous(command)
        if warning:
            return (
                f"Blocked: {warning}\n"
                f"Command: {command}\n"
                "If intentional, modify the command to be more specific."
            )

        with _cwd_lock:
            cwd = _cwd or os.getcwd()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            # track cd so the next command runs in the right place
            if result.returncode == 0:
                _update_cwd(command, cwd)

            out = result.stdout
            if result.stderr:
                out += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                out += f"\n[exit code: {result.returncode}]"

            # keep head + tail to preserve useful info
            if len(out) > 15_000:
                out = (
                    out[:6000]
                    + f"\n\n... truncated ({len(out)} chars total) ...\n\n"
                    + out[-3000:]
                )
            return out.strip() or "(no output)"

        except subprocess.TimeoutExpired:
            return f"[error] Command timed out after {timeout}s"
        except Exception as e:
            return f"[error] {e}"
