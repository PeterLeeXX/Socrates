"""Session persistence - save and resume conversations."""

import json
import re
import time
import uuid
from pathlib import Path

SESSIONS_DIR = Path.home() / ".socrates" / "sessions"
_SAFE_SESSION_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _normalize_session_id(session_id: str | None) -> str:
    if not session_id:
        return _new_session_id()

    name = session_id.strip().replace("\\", "/").split("/")[-1]
    name = _SAFE_SESSION_RE.sub("-", name).strip(".-_")
    return name or _new_session_id()


def _new_session_id() -> str:
    return f"session_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _session_path(session_id: str) -> Path:
    path = (SESSIONS_DIR / f"{_normalize_session_id(session_id)}.json").resolve()
    root = SESSIONS_DIR.resolve()
    if root != path.parent:
        raise ValueError("Invalid session id")
    return path


def save_session(
    messages: list[dict],
    model: str,
    session_id: str | None = None,
) -> str:
    """Save conversation to disk. Returns the session id."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = _normalize_session_id(session_id)

    data = {
        "model": model,
        "messages": messages,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    path = _session_path(session_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return session_id


def load_session(session_id: str) -> tuple[list[dict], str] | None:
    """Load a session. Returns (messages, model) or None."""
    path = _session_path(session_id)
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    return data["messages"], data["model"]


def list_sessions() -> list[dict]:
    """List saved sessions with metadata."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    for p in sorted(SESSIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            msg_count = len(data.get("messages", []))
            sessions.append({
                "id": p.stem,
                "model": data.get("model", "?"),
                "messages": msg_count,
                "saved_at": data.get("saved_at", "?"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sessions
