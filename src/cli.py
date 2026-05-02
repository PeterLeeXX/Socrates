"""CLI entry point for Socrates."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table


def main():
    """CLI main entry point."""
    import os
    if os.environ.get("SOCRATES_DEBUG", "").lower() in ("1", "true", "yes"):
        import logging
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s %(name)s %(message)s",
            stream=sys.stderr,
        )

    if len(sys.argv) == 2 and sys.argv[1] in ['--version', '-v', '-V']:
        from src import __version__
        print(f"socrates version {__version__} (Python)")
        return 0

    # Subcommands are matched BEFORE the main parser. We only need to detect
    # `login` / `config`; everything else falls through to the main parser.
    argv = sys.argv[1:]
    for idx, token in enumerate(argv):
        if token.startswith('-'):
            continue
        if token in ('login', 'config'):
            if token == 'login':
                return handle_login()
            return show_config()
        break

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from src import __version__
        print(f"socrates version {__version__} (Python)")
        return 0

    if args.config:
        return show_config()

    # Resolve permission state ONCE here so the REPL honors it consistently.
    _resolve_permission_state(args)

    return start_repl(
        stream=args.stream,
        permission_mode=args._resolved_permission_mode,
        is_bypass_permissions_mode_available=args._resolved_is_bypass_available,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="socrates",
        description="Socrates - Claude Code Python Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  socrates --version                   Show version
  socrates login                       Configure API keys
  socrates config                      Show current configuration
  socrates --stream                    Start REPL with live response rendering
  socrates                             Start interactive REPL
""",
    )

    parser.add_argument('--version', action='store_true', help='Show version information')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    parser.add_argument('--stream', action='store_true', help='Enable live rendering in REPL')

    # ---- Permissions ----
    # ``--dangerously-skip-permissions`` and ``--allow-dangerously-skip-permissions``
    # apply to the REPL, so they live in a top-level
    permissions_group = parser.add_argument_group("permissions")
    permissions_group.add_argument(
        '--dangerously-skip-permissions',
        dest='dangerously_skip_permissions',
        action='store_true',
        help=(
            'Bypass all permission checks. Recommended only for sandboxes '
            'with no internet access.'
        ),
    )
    permissions_group.add_argument(
        '--allow-dangerously-skip-permissions',
        dest='allow_dangerously_skip_permissions',
        action='store_true',
        help=(
            'Enable bypassing all permission checks as an option, without it '
            'being enabled by default. Recommended only for sandboxes with '
            'no internet access.'
        ),
    )
    permissions_group.add_argument(
        '--permission-mode',
        dest='permission_mode',
        choices=('default', 'plan', 'acceptEdits', 'bypassPermissions', 'dontAsk'),
        default=None,
        help='Initial permission mode (default: default)',
    )

    # Subcommands are intercepted in ``main`` before argparse runs. Listing
    # them here purely for ``--help`` documentation.
    commands_group = parser.add_argument_group("subcommands")
    commands_group.add_argument(
        '--_commands_doc',
        help=argparse.SUPPRESS,
    )
    parser.epilog = (parser.epilog or "") + (
        "\nSubcommands:\n"
        "  login    Configure API keys (interactive)\n"
        "  config   Show current configuration\n"
    )
    return parser


def _resolve_permission_state(args) -> None:
    """Resolve and stash permission state on ``args``.

    Computes the effective :class:`PermissionMode` from the CLI flags and
    settings, runs the root/sudo safety gate, and emits a single log line
    when either bypass flag was passed. Stashes the result on ``args`` so
    the REPL can read it without re-deriving.

    """
    import logging as _logging

    from src.permissions.dangerous_safety import (
        enforce_dangerous_skip_permissions_safety,
    )
    from src.permissions.modes import (
        has_allow_bypass_permissions_mode,
        initial_permission_mode_from_cli,
    )

    dangerously = bool(getattr(args, 'dangerously_skip_permissions', False))
    allow_dangerously = bool(getattr(args, 'allow_dangerously_skip_permissions', False))
    permission_mode_cli = getattr(args, 'permission_mode', None)

    # Safety gate first - refuse to run as root outside a sandbox.
    enforce_dangerous_skip_permissions_safety(
        bypass_requested=dangerously or allow_dangerously,
    )

    mode = initial_permission_mode_from_cli(
        permission_mode_cli=permission_mode_cli,
        dangerously_skip_permissions=dangerously,
    )

    is_bypass_available = (
        dangerously
        or allow_dangerously
        or has_allow_bypass_permissions_mode()
    )

    # Stash on args so downstream callers don't need to re-derive.
    args._resolved_permission_mode = mode
    args._resolved_is_bypass_available = is_bypass_available

    if dangerously or allow_dangerously:
        _logging.getLogger("socrates.permissions").info(
            "permission flags: dangerously_skip=%s allow_dangerously_skip=%s mode=%s",
            dangerously,
            allow_dangerously,
            mode,
        )


def _show_provider_defaults_table() -> None:
    """Print a table showing available providers and their defaults."""
    from src.providers import PROVIDER_INFO

    console = Console()
    table = Table(title="Available Providers & Defaults", show_header=True, header_style="bold")
    table.add_column("Provider", style="cyan")
    table.add_column("Default Model", style="magenta")
    table.add_column("Base URL", style="green")

    for name, info in PROVIDER_INFO.items():
        table.add_row(
            f"{name} ({info['label']})",
            info["default_model"],
            info["default_base_url"],
        )

    console.print(table)
    console.print()


def handle_login():
    """Interactive API configuration."""
    console = Console()
    console.print("\n[bold blue]Socrates - API Configuration[/bold blue]\n")

    _show_provider_defaults_table()

    from src.providers import PROVIDER_INFO
    provider_names = list(PROVIDER_INFO.keys())

    provider = Prompt.ask(
        "Select LLM provider",
        choices=provider_names,
        default="anthropic"
    )

    info = PROVIDER_INFO[provider]

    api_key = Prompt.ask(
        f"Enter {provider.upper()} API Key",
        password=True
    )

    if not api_key:
        console.print("\n[red]Error: API Key cannot be empty[/red]")
        return 1

    console.print(f"\n[dim]Default:[/dim] {info['default_base_url']}")
    base_url = Prompt.ask(
        f"{provider.upper()} Base URL",
        default=info["default_base_url"]
    )

    console.print(f"\n[dim]Available models:[/dim] {', '.join(info['available_models'])}")
    console.print(f"[dim]Default:[/dim] [bold]{info['default_model']}[/bold]")
    default_model = Prompt.ask(
        f"{provider.upper()} Default Model",
        default=info["default_model"]
    )

    from src.config import set_api_key, set_default_provider

    set_api_key(provider, api_key=api_key, base_url=base_url, default_model=default_model)
    set_default_provider(provider)

    console.print(f"\n[green]OK {provider.upper()} API Key saved successfully![/green]")
    console.print(f"[green]OK Default provider set to: {provider}[/green]\n")
    return 0


def show_config():
    """Show current configuration."""
    console = Console()

    try:
        from src.config import load_config, get_config_path

        config = load_config()
        config_path = get_config_path()

        console.print(f"\n[bold]Configuration File:[/bold] {config_path}\n")
        console.print("[bold]Current Configuration:[/bold]\n")

        console.print(f"[cyan]Default Provider:[/cyan] {config.get('default_provider', 'Not set')}")

        console.print("\n[cyan]Configured Providers:[/cyan]")
        for provider_name, provider_config in config.get("providers", {}).items():
            api_key = provider_config.get("api_key", "")
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "Not set"

            console.print(f"\n  [yellow]{provider_name.upper()}:[/yellow]")
            console.print(f"    API Key: {masked_key}")
            console.print(f"    Base URL: {provider_config.get('base_url', 'Not set')}")
            console.print(f"    Default Model: {provider_config.get('default_model', 'Not set')}")

        console.print()

    except Exception as e:
        console.print(f"\n[red]Error loading configuration: {e}[/red]\n")
        return 1

    return 0


def start_repl(
    stream: bool = False,
    *,
    permission_mode: str = "default",
    is_bypass_permissions_mode_available: bool = False,
):
    """Start interactive REPL.

    ``permission_mode`` and ``is_bypass_permissions_mode_available`` are
    resolved by :func:`_resolve_permission_state`. They control whether
    the in-process tool registry will short-circuit permission checks
    for the user (when ``--dangerously-skip-permissions`` is set).
    """
    from src.config import get_default_provider
    from src.repl import SocratesREPL

    provider = get_default_provider()
    repl = SocratesREPL(
        provider_name=provider,
        stream=stream,
        permission_mode=permission_mode,
        is_bypass_permissions_mode_available=is_bypass_permissions_mode_available,
    )
    repl.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
