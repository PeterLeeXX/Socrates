# Socrates

Small Python coding agent for the terminal. It uses LiteLLM for model access, Rich for terminal output, and a compact built-in toolset for reading, editing, searching, and running code.

Socrates is intentionally simple: the core agent loop lives in a handful of files, the tool schemas are plain Python, and the runtime is easy to inspect or extend.

## Features

- Multi-provider model registry via LiteLLM
- Streaming terminal responses
- Tool-calling agent loop
- Built-in tools for shell, file read/write/edit, glob, and grep
- Parallel execution for multiple tool calls
- Context compression for long sessions
- Session save/resume
- `.env` support from the current working directory and `~/.socrates/.env`
- Dangerous shell command blocking for common footguns

## Install

```bash
pip install socrates
```

For local development:

```bash
git clone https://github.com/PeterLeeXX/Socrates.git
cd Socrates
pip install -e ".[dev]"
pytest -q
```

## Quick Start

Set an API key for the provider you want to use:

```bash
export DEEPSEEK_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...
export GEMINI_API_KEY=...
```

Start the interactive REPL:

```bash
socrates
```

Use a specific model:

```bash
socrates -m qwen3.6-plus
socrates -m gpt-5.5
socrates -m claude-sonnet-4.6
socrates -m gemini-3.5-flash
```

Run one prompt and exit:

```bash
socrates "find the failing test and fix it"
socrates -p "summarize the project structure"
```

Resume a saved session:

```bash
socrates --resume SESSION_ID
```

## Configuration

Socrates loads `.env` from:

1. The current working directory
2. `~/.socrates/.env`

Common variables:

| Variable | Purpose |
| --- | --- |
| `SOCRATES_MODEL` | Default model registry key |
| `SOCRATES_<PROVIDER>_API_KEY` | Provider-specific API key override |
| `SOCRATES_<PROVIDER>_API_BASE` | Provider-specific API base override |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GEMINI_API_KEY` | Gemini API key |
| `DASHSCOPE_API_KEY` | Qwen/DashScope API key |
| `MOONSHOT_API_KEY` | Moonshot/Kimi API key |
| `ZAI_API_KEY` | Z.ai/GLM API key |

Example:

```bash
SOCRATES_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=sk-...
```

## Model Keys

Use `/models` inside the REPL to see the current registry.

Common keys:

| Key | Provider |
| --- | --- |
| `deepseek-v4-flash` | DeepSeek |
| `deepseek-v4-pro` | DeepSeek |
| `qwen3.6-plus` | Qwen/DashScope |
| `qwen3.6-flash` | Qwen/DashScope |
| `gpt-5.5` | OpenAI |
| `gpt-5.5-pro` | OpenAI |
| `claude-sonnet-4.6` | Anthropic |
| `claude-opus-4.7` | Anthropic |
| `gemini-3.5-flash` | Google Gemini |
| `kimi-k2.6` | Moonshot/Kimi |
| `glm-5.1` | Z.ai |

## Tools

The model can call these built-in tools:

| Tool | Purpose |
| --- | --- |
| `bash` | Run shell commands with safety checks and cwd tracking |
| `read_file` | Read text files with line numbers, offset, and limit |
| `write_file` | Create or overwrite files |
| `edit_file` | Replace exact text and return a unified diff |
| `glob` | Find files by glob pattern |
| `grep` | Search text files with regex |

## REPL Commands

| Command | Description |
| --- | --- |
| `/help` | Show help |
| `/model` | Show the current model |
| `/model <key>` | Switch model |
| `/models` | List registered model keys |
| `/tokens` | Show token and cost estimate |
| `/diff` | Show files modified by write/edit tools |
| `/compact` | Compress the current conversation context |
| `/save [name]` | Save the session |
| `/sessions` | List saved sessions |
| `/clear` | Clear conversation history except the system prompt |
| `/quit` | Exit |

Input controls:

- Enter sends the message
- Esc+Enter inserts a newline
- Ctrl+C cancels the current input or run
- Ctrl+D exits

## Architecture

```text
socrates/
  cli.py              REPL, one-shot mode, slash commands
  agent.py            Agent loop, LLM calls, tool execution
  llm.py              LiteLLM wrapper and streaming chunk normalization
  context.py          Message history and compression
  config.py           Model registry and environment configuration
  session.py          Local session save/load/list helpers
  prompts/system.py   System prompt
  tools/              Built-in tool implementations
```

The runtime flow is:

1. Add the user message to context
2. Send messages and tool schemas to the model
3. Stream assistant text to the terminal
4. Execute tool calls when requested
5. Append tool results to context
6. Repeat until the model returns without tool calls

Context compression happens when the conversation approaches the configured token threshold. Socrates first truncates older long tool outputs, then summarizes older turns if needed.

## AG-UI Status

`ag-ui-protocol` is listed as a dependency because Socrates is being prepared for an AG-UI event adapter. The current CLI does not yet expose an AG-UI HTTP/SSE endpoint, assistant-ui frontend, or Tauri desktop shell.

The intended direction is a thin adapter:

```text
Socrates agent loop -> internal agent events -> AG-UI BaseEvent stream -> assistant-ui
```

## Library Use

```python
from socrates import Agent, Config

config = Config.from_env()
config.resolve_model("deepseek-v4-flash")

agent = Agent(config)
agent.run("inspect the tests and explain what they cover")
```

## Tests

```bash
pytest -q
```

## License

MIT. See `LICENSE`.
