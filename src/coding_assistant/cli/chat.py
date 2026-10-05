"""
Interactive Terminal Chat Client for CodeCopilot

Provides a friendly terminal interface to interact with the CodeCopilot server.

Features:
  • Natural language queries about your codebase
  • Safe tool execution (files, shell, tests, etc.)
  • Real-time responses with structured reasoning
  • Slash commands for navigation and control

Usage:
  coding-assistant chat --workspace /path/to/project
  
Examples:
  "What are the main entry points?"
  "Find all TODO comments"
  "Explain the authentication flow"
  "/workspace /path/to/other/project"
  "/status" - show current settings
  "/help" - list all commands

Author: CodeCopilot Team
"""

from __future__ import annotations

import sys
from pathlib import Path

from coding_assistant.cli.client import ApiClient, ApiError, ApprovalView
from coding_assistant.config import Settings, get_settings


class _Colors:
    """ANSI color formatting for terminal output."""
    
    def __init__(self, enabled: bool) -> None:
        self._on = enabled

    def _c(self, code: str, text: str) -> str:
        """Apply ANSI color code if colors are enabled."""
        if not self._on:
            return text
        return f"\033[{code}m{text}\033[0m"

    def user_label(self, text: str) -> str:
        """Cyan: User input label."""
        return self._c("36", text)

    def assistant_label(self, text: str) -> str:
        """Green: Assistant response label."""
        return self._c("32", text)

    def dim(self, text: str) -> str:
        """Dim/gray: Helper text."""
        return self._c("2", text)

    def error(self, text: str) -> str:
        """Red: Error messages."""
        return self._c("31", text)

    def warn(self, text: str) -> str:
        """Yellow: Warning messages."""
        return self._c("33", text)


# List of supported slash commands for quick reference
SLASH_COMMANDS = frozenset({"help", "exit", "quit", "workspace", "status"})


def parse_slash_command(line: str) -> tuple[str | None, str]:
    """
    Parse a slash command from user input.
    
    Returns:
      (command_name, argument) for /cmd args
      (None, original_line) for normal text input
      
    Example:
      parse_slash_command("/workspace /home/user/project")
      → ("workspace", "/home/user/project")
      
      parse_slash_command("What is this?")
      → (None, "What is this?")
    """
    stripped = line.strip()
    if not stripped.startswith("/"):
        return None, line
    parts = stripped[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def run_chat(
    *,
    api_url: str,
    workspace: Path,
    token: str | None = None,
    poll_interval: float = 1.0,
    run_timeout: float = 300.0,
    use_color: bool = True,
) -> int:
    colors = _Colors(use_color and sys.stdout.isatty())
    workspace = workspace.resolve()

    print(colors.dim(f"API: {api_url}"))
    print(colors.dim(f"Workspace: {workspace}"))
    print(colors.dim("Commands: /help /workspace <path> /status /exit"))
    print()

    with ApiClient(api_url, token=token) as client:
        if not client.health():
            print(
                colors.error(
                    "Cannot reach the API. Start the server in another terminal:\n"
                    "  coding-assistant serve"
                ),
                file=sys.stderr,
            )
            return 1

        if not workspace.is_dir():
            print(colors.error(f"Workspace not found: {workspace}"), file=sys.stderr)
            return 1

        workspace_str = str(workspace)

        while True:
            try:
                line = input(colors.user_label("You: ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                print(colors.dim("Goodbye."))
                return 0

            if not line:
                continue

            cmd, arg = parse_slash_command(line)
            if cmd in ("exit", "quit"):
                print(colors.dim("Goodbye."))
                return 0
            if cmd == "help":
                _print_help(colors)
                continue
            if cmd == "workspace":
                if not arg:
                    print(colors.warn("Usage: /workspace <path>"))
                    continue
                workspace = Path(arg).expanduser().resolve()
                if not workspace.is_dir():
                    print(colors.error(f"Not a directory: {workspace}"))
                    continue
                workspace_str = str(workspace)
                print(colors.dim(f"Workspace: {workspace_str}"))
                continue
            if cmd == "status":
                print(colors.dim(f"API: {api_url}  |  Workspace: {workspace_str}"))
                continue
            if cmd is not None:
                print(colors.warn(f"Unknown command: /{cmd}. Try /help"))
                continue

            message = line
            print(colors.dim("Thinking…"), end="", flush=True)
            last_status: str | None = None

            def on_status(status: str) -> None:
                nonlocal last_status
                if status == last_status:
                    return
                last_status = status
                print(colors.dim(f" [{status}]"), end="", flush=True)

            def on_approval(approval: ApprovalView) -> bool:
                print()
                print(colors.warn(f"Approval required: {approval.action_type}"))
                if approval.payload:
                    preview = str(approval.payload)
                    if len(preview) > 200:
                        preview = preview[:200] + "…"
                    print(colors.dim(preview))
                while True:
                    try:
                        answer = input("Approve? [y/N]: ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return False
                    if answer in ("y", "yes"):
                        return True
                    if answer in ("n", "no", ""):
                        return False
                    print(colors.warn("Please answer y or n."))

            try:
                run = client.create_run(workspace_str, message)
                finished = client.wait_for_run(
                    run.id,
                    poll_interval=poll_interval,
                    timeout_seconds=run_timeout,
                    on_status=on_status,
                    on_approval=on_approval,
                )
            except ApiError as exc:
                print()
                print(colors.error(f"Error: {exc}"), file=sys.stderr)
                continue

            print()
            text = finished.final_response or ""
            if finished.status == "completed" and text and not text.startswith("Planning failed"):
                print(colors.assistant_label("Assistant:"), text or "(no response)")
            else:
                detail = finished.error or text or finished.status
                print(colors.error(f"Run failed ({finished.status}): {detail}"), file=sys.stderr)
            print()


def _print_help(colors: _Colors) -> None:
    print(colors.dim("""Slash commands:
  /help              Show this help
  /workspace <path>  Change repo root for tool execution
  /status            Show API URL and workspace
  /exit, /quit       Leave chat

Each message starts a new agent run on the server (tools + planner loop).
Ensure `coding-assistant serve` is running and LLM keys are set in .env."""))


def chat_from_settings(
    settings: Settings | None = None,
    *,
    api_url: str | None = None,
    workspace: Path | str | None = None,
    token: str | None = None,
    poll_interval: float | None = None,
    run_timeout: float | None = None,
    use_color: bool = True,
) -> int:
    s = settings or get_settings()
    return run_chat(
        api_url=api_url or s.chat_api_base_url,
        workspace=Path(workspace or s.workspace_root),
        token=token or s.chat_api_token,
        poll_interval=poll_interval if poll_interval is not None else s.chat_poll_interval_seconds,
        run_timeout=run_timeout if run_timeout is not None else float(s.chat_run_timeout_seconds),
        use_color=use_color,
    )
