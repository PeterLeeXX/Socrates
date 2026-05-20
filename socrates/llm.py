"""LLM abstraction layer - supports 100+ providers via litellm."""

import json
import os
from typing import Generator

os.environ.setdefault("LITELLM_LOG", "ERROR")

import litellm
from litellm import completion, token_counter

# suppress litellm's noisy debug logs
litellm.suppress_debug_info = True


class LLMClient:
    """Wrapper around litellm for streaming tool-call conversations."""

    def __init__(self, model: str, api_base: str | None = None, api_key: str | None = None):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key

        # running totals
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = True,
    ) -> Generator[dict, None, None]:
        """
        Send messages to the LLM and yield response chunks.

        Yields dicts with keys:
          - {"type": "text", "content": "..."} for text chunks
          - {"type": "tool_call", "calls": [...]} when the model wants to call tools
          - {"type": "usage", "input_tokens": N, "output_tokens": N, "cost": float}
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.api_key:
            kwargs["api_key"] = self.api_key

        if not stream:
            yield from self._non_streaming(**kwargs)
            return

        yield from self._streaming(**kwargs)

    def _streaming(self, **kwargs) -> Generator[dict, None, None]:
        """Handle streaming responses, assembling tool calls from deltas."""
        response = completion(**kwargs)

        full_text = ""
        tool_calls_by_index: dict[int, dict] = {}

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # text content
            if delta.content:
                full_text += delta.content
                yield {"type": "text", "content": delta.content}

            # tool call deltas - need to assemble them piece by piece
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_by_index:
                        tool_calls_by_index[idx] = {
                            "id": "",
                            "function": {"name": "", "arguments": ""},
                        }
                    entry = tool_calls_by_index[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["function"]["arguments"] += tc_delta.function.arguments

        # emit assembled tool calls
        if tool_calls_by_index:
            calls = []
            for idx in sorted(tool_calls_by_index.keys()):
                raw = tool_calls_by_index[idx]
                try:
                    args = json.loads(raw["function"]["arguments"]) if raw["function"]["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                calls.append({
                    "id": raw["id"],
                    "name": raw["function"]["name"],
                    "arguments": args,
                })
            yield {"type": "tool_call", "calls": calls}

        # try to get usage from the last chunk or estimate
        self._track_usage(kwargs.get("messages", []), full_text, kwargs.get("model", self.model))

    def _non_streaming(self, **kwargs) -> Generator[dict, None, None]:
        """Handle non-streaming responses."""
        kwargs.pop("stream", None)
        response = completion(**kwargs, stream=False)

        msg = response.choices[0].message

        if msg.content:
            yield {"type": "text", "content": msg.content}

        if msg.tool_calls:
            calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
            yield {"type": "tool_call", "calls": calls}

        # usage info
        if response.usage:
            inp = response.usage.prompt_tokens or 0
            out = response.usage.completion_tokens or 0
            self.total_input_tokens += inp
            self.total_output_tokens += out
            try:
                cost = litellm.completion_cost(response)
                self.total_cost += cost
            except Exception:
                cost = 0.0
            yield {"type": "usage", "input_tokens": inp, "output_tokens": out, "cost": cost}

    def _track_usage(self, messages: list, output_text: str, model: str):
        """Best-effort token tracking for streaming responses."""
        try:
            inp = token_counter(model=model, messages=messages)
            out = token_counter(model=model, text=output_text)
            self.total_input_tokens += inp
            self.total_output_tokens += out
            # cost estimation - rough but better than nothing
            try:
                cost = litellm.completion_cost(
                    model=model,
                    prompt_tokens=inp,
                    completion_tokens=out,
                )
                self.total_cost += cost
            except Exception:
                pass
        except Exception:
            pass

    def count_tokens(self, messages: list) -> int:
        """Count tokens in a message list."""
        try:
            return token_counter(model=self.model, messages=messages)
        except Exception:
            # rough fallback: ~4 chars per token
            total_chars = sum(len(str(m.get("content", ""))) for m in messages)
            return total_chars // 4

    @property
    def usage_summary(self) -> str:
        parts = [f"tokens: {self.total_input_tokens + self.total_output_tokens:,}"]
        if self.total_cost > 0:
            parts.append(f"cost: ${self.total_cost:.4f}")
        return " | ".join(parts)
