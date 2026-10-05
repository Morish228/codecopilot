"""
CodeCopilot CLI Entry Point

Two main commands:
  1. serve     - Start the FastAPI server (required first)
  2. chat      - Interactive terminal chat client (requires server running)

Usage:
  coding-assistant serve [--host 127.0.0.1] [--port 8000] [--reload]
  coding-assistant chat [--workspace /path] [--api-url http://localhost:8000]

Examples:
  # Terminal 1: Start server
  coding-assistant serve
  
  # Terminal 2: Connect chat client
  coding-assistant chat --workspace ~/my-project
"""

import argparse

import uvicorn

from coding_assistant.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="coding-assistant",
        description="Local coding assistant — API server and terminal chat client.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 'serve' command: Start the FastAPI server with LangGraph runtime
    serve = sub.add_parser("serve", help="Start the FastAPI server")
    serve.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    serve.add_argument("--reload", action="store_true", help="Auto-reload on file changes (dev only)")

    # 'chat' command: Start interactive terminal client
    chat = sub.add_parser("chat", help="Interactive terminal chat (requires serve running)")
    chat.add_argument(
        "--api-url",
        default=None,
        help="API base URL (default: CHAT_API_BASE_URL env var or http://127.0.0.1:8000)",
    )
    chat.add_argument(
        "--workspace",
        default=None,
        help="Repository root for tool execution (default: WORKSPACE_ROOT env var)",
    )
    chat.add_argument("--token", default=None, help="Bearer token if AUTH_REQUIRED=true")
    chat.add_argument("--timeout", type=int, default=None, help="Max seconds per run")
    chat.add_argument("--no-color", action="store_true", help="Disable ANSI colors in terminal")

    args = parser.parse_args()
    
    if args.command == "serve":
        # Start the FastAPI server
        print(f"🚀 Starting CodeCopilot server at http://{args.host}:{args.port}")
        print(f"📖 API documentation at http://{args.host}:{args.port}/docs")
        uvicorn.run(
            "coding_assistant.app:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return

    if args.command == "chat":
        # Start interactive terminal chat
        from coding_assistant.cli.chat import chat_from_settings
        from coding_assistant.config import get_settings

        settings = get_settings()
        raise SystemExit(
            chat_from_settings(
                settings,
                api_url=args.api_url,
                workspace=args.workspace,
                token=args.token,
                run_timeout=float(args.timeout) if args.timeout is not None else None,
                use_color=not args.no_color,
            )
        )


if __name__ == "__main__":
    main()
