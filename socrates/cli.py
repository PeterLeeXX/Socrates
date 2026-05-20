"""CLI interface - the REPL that users interact with."""

import argparse
import os

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings

from socrates import __version__
from socrates.config import Config, MODEL_REGISTRY
from socrates.agent import Agent
from socrates.session import save_session, load_session, list_sessions


console = Console()


def _short_model(model: str) -> str:
    """Strip the provider prefix for display."""
    return model.split("/")[-1] if "/" in model else model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Socrates - AI coding agent for any LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  socrates                          Start with default model (DeepSeek)
  socrates -m claude-sonnet-4.6     Use Claude
  socrates -m gpt-5.5               Use GPT-5.5
  socrates -m deepseek-v4-flash     Use DeepSeek
  socrates -m qwen3.6-plus          Use Qwen
  socrates -m gemini-3.5-flash      Use Gemini
  socrates "fix the bug in main.py" One-shot mode
""",
    )
    parser.add_argument(
        "-m", "--model", type=str, default=None,
        help="Model registry key to use (see /models)",
    )
    parser.add_argument(
        "--api-base", type=str, default=None,
        help="Custom API base URL",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="API key (can also set via env vars)",
    )
    parser.add_argument(
        "-r", "--resume", type=str, default=None, metavar="SESSION_ID",
        help="Resume a saved session",
    )
    parser.add_argument(
        "-p", "--prompt", type=str, default=None,
        help="One-shot prompt (skip interactive mode)",
    )
    parser.add_argument(
        "prompt_positional", nargs="*",
        help="One-shot prompt (alternative to -p)",
    )
    return parser.parse_args()


def _apply_cli_overrides(config: Config, args: argparse.Namespace):
    if args.api_base:
        config.api_base = args.api_base
    if args.api_key:
        config.api_key = args.api_key


def main():
    args = parse_args()
    config = Config.from_env()

    if args.model:
        try:
            config.resolve_model(args.model)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return
    _apply_cli_overrides(config, args)

    agent = Agent(config)

    # resume a saved session
    if args.resume:
        loaded = load_session(args.resume)
        if loaded:
            msgs, model = loaded
            try:
                config.resolve_model(model)
            except ValueError as e:
                console.print(f"[red]{e}[/red]")
                console.print("[yellow]Saved session uses an old model value. Start without --resume and choose a registry key with /model.[/yellow]")
                return
            _apply_cli_overrides(config, args)
            agent = Agent(config)
            agent.ctx.messages = msgs
            console.print(f"[dim]Resumed session: {args.resume}[/dim]")
        else:
            console.print(f"[red]Session not found: {args.resume}[/red]")
            return

    # one-shot mode
    one_shot = args.prompt or (" ".join(args.prompt_positional) if args.prompt_positional else None)
    if one_shot:
        agent.run(one_shot)
        return

    # interactive REPL
    console.print(f"\n[bold green]  Socrates v{__version__}[/bold green]")
    console.print(f"  Model: [bold]{config.model_key}[/bold]  |  cwd: {os.getcwd()}")
    console.print("  /help for commands  |  Esc+Enter for newline  |  Ctrl+D to exit\n")

    history_dir = os.path.expanduser("~/.socrates")
    os.makedirs(history_dir, exist_ok=True)

    # key bindings: Enter submits, Esc+Enter inserts newline
    kb = KeyBindings()

    @kb.add("enter")
    def _submit(event):
        event.current_buffer.validate_and_handle()

    @kb.add("escape", "enter")
    def _newline(event):
        event.current_buffer.insert_text("\n")

    session = PromptSession(
        history=FileHistory(os.path.join(history_dir, "history")),
        auto_suggest=AutoSuggestFromHistory(),
        multiline=True,
        key_bindings=kb,
    )

    while True:
        try:
            user_input = session.prompt(
                "\n> ",
                prompt_continuation="… ",
            ).strip()
        except KeyboardInterrupt:
            console.print("[dim]Interrupted[/dim]")
            continue
        except EOFError:
            console.print("[dim]Bye![/dim]")
            break

        if not user_input:
            continue

        # slash commands
        if user_input.startswith("/"):
            if _handle_command(user_input, config, agent):
                continue

        # run the agent
        try:
            agent.run(user_input)
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")

        # status bar
        console.print(f"[dim]{config.model_key} | {agent.llm.usage_summary}[/dim]")


def _handle_command(cmd: str, config: Config, agent: Agent) -> bool:
    """Handle slash commands. Returns True if command was recognized."""
    parts = cmd.split(None, 1)
    command = parts[0].lower()

    if command in ("/help", "/h"):
        console.print("""\
[bold]Commands:[/bold]
  /model           Show current model
  /model <name>    Switch model (e.g. /model gpt-5.5, /model qwen3.6-plus)
  /models          List available model keys
  /tokens          Token usage and cost estimate
  /diff            Files modified this session
  /compact         Compress conversation context
  /save [name]     Save session
  /sessions        List saved sessions
  /clear           Clear conversation history
  /quit            Exit

[bold]Input:[/bold]
  Enter            Send message
  Esc + Enter      Insert newline (multiline input)
  Ctrl+C           Cancel current operation
  Ctrl+D           Exit""")
        return True

    if command == "/model":
        if len(parts) < 2:
            console.print(f"Current model: [bold]{config.model_key}[/bold] ({config.model})")
            return True
        new_model = parts[1].strip()
        try:
            config.resolve_model(new_model)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return True
        agent.apply_config()
        console.print(f"Switched to [bold]{config.model_key}[/bold]")
        return True

    if command == "/models":
        current_provider = None
        for key, spec in sorted(MODEL_REGISTRY.items(), key=lambda item: (item[1].provider, item[0])):
            if spec.provider != current_provider:
                current_provider = spec.provider
                console.print(f"\n[bold]{current_provider.title()}[/bold]")
            console.print(f"  {key:<24s} -> {spec.litellm_model}")
        return True

    if command == "/tokens":
        llm = agent.llm
        total = llm.total_input_tokens + llm.total_output_tokens
        line = f"Tokens: {llm.total_input_tokens:,} in + {llm.total_output_tokens:,} out = {total:,} total"
        if llm.total_cost > 0:
            line += f"  (~${llm.total_cost:.4f})"
        console.print(line)
        return True

    if command == "/diff":
        from socrates.tools.edit_file import _changed_files
        if not _changed_files:
            console.print("[dim]No files modified this session.[/dim]")
        else:
            console.print(f"[bold]Files modified ({len(_changed_files)}):[/bold]")
            for f in sorted(_changed_files):
                console.print(f"  {f}")
        return True

    if command == "/compact":
        console.print("[dim]Compressing context...[/dim]")
        agent.ctx.compress()
        console.print(f"[dim]Done. Context: ~{agent.ctx.token_count:,} tokens[/dim]")
        return True

    if command == "/save":
        name = parts[1].strip() if len(parts) > 1 else None
        sid = save_session(agent.ctx.get_messages(), config.model_key, name)
        console.print(f"Session saved: [bold]{sid}[/bold]")
        return True

    if command == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
        else:
            for s in sessions[:20]:
                console.print(
                    f"  {s['id']:<30s}  {s['model']:<24s}  "
                    f"{s['messages']} msgs  {s['saved_at']}"
                )
        return True

    if command == "/clear":
        agent.ctx.reset()
        console.print("[dim]Conversation cleared.[/dim]")
        return True

    if command in ("/quit", "/exit", "/q"):
        raise EOFError()

    return False


if __name__ == "__main__":
    main()
