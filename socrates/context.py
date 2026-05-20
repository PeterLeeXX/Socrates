"""Context window management - keeps conversations within token limits.

Two-phase compression (inspired by Claude Code):
  1. Snip long tool outputs first (cheap, keeps conversation structure)
  2. Summarize old conversation turns if still over threshold
"""

from socrates.llm import LLMClient

_TOOL_SNIP_THRESHOLD = 8000


class ContextManager:
    """Tracks message history and compresses when approaching the token limit."""

    def __init__(self, llm: LLMClient, max_tokens: int, compress_threshold: float = 0.7):
        self.llm = llm
        self.max_tokens = max_tokens
        self.compress_threshold = compress_threshold
        self.messages: list[dict] = []

    def add(self, message: dict):
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        return list(self.messages)

    @property
    def token_count(self) -> int:
        return self.llm.count_tokens(self.messages)

    def needs_compression(self) -> bool:
        return self.token_count > int(self.max_tokens * self.compress_threshold)

    def compress(self):
        """Snip tool outputs first, then summarize old turns if needed."""
        self._snip_tool_outputs()
        if self.needs_compression():
            self._summarize_old()

    def _snip_tool_outputs(self):
        """Truncate long tool results, keeping head + tail."""
        cutoff = max(0, len(self.messages) - 6)
        for i in range(cutoff):
            msg = self.messages[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str) or len(content) <= _TOOL_SNIP_THRESHOLD:
                continue
            half = _TOOL_SNIP_THRESHOLD // 2
            snipped = (
                content[:half]
                + f"\n\n[truncated {len(content)} -> {_TOOL_SNIP_THRESHOLD} chars]\n\n"
                + content[-half:]
            )
            self.messages[i] = {**msg, "content": snipped}

    def _summarize_old(self):
        """Replace old messages with a compressed summary."""
        if len(self.messages) < 6:
            return

        system = self.messages[0] if self.messages[0]["role"] == "system" else None
        recent = self.messages[-6:]
        start = 1 if system else 0
        middle = self.messages[start:-6]

        if not middle:
            return

        parts = []
        for msg in middle:
            role = msg["role"]
            content = msg.get("content") or ""
            if isinstance(content, str) and content.strip():
                preview = content[:300] + "..." if len(content) > 300 else content
                parts.append(f"[{role}] {preview}")
            elif role == "assistant" and msg.get("tool_calls"):
                names = [tc["function"]["name"] for tc in msg.get("tool_calls", [])]
                parts.append(f"[assistant] called: {', '.join(names)}")
            elif role == "tool":
                parts.append("[tool result]")

        summary = "[Conversation compressed]\n" + "\n".join(parts[-15:])
        compressed = [{"role": "assistant", "content": summary}]
        self.messages = ([system] if system else []) + compressed + recent

    def reset(self):
        """Clear everything except the system prompt."""
        system = self.messages[0] if self.messages and self.messages[0]["role"] == "system" else None
        self.messages = [system] if system else []
