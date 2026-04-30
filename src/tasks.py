from __future__ import annotations

from .task import PortingTask


def default_tasks() -> list[PortingTask]:
    return [
        PortingTask('workspace-manifest', 'Track the current Python module surface'),
        PortingTask('command-inventory', 'Maintain command inventory coverage'),
        PortingTask('tool-inventory', 'Maintain tool inventory coverage'),
    ]
