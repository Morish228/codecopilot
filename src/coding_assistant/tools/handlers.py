"""Backward-compatible handler aliases."""

from pathlib import Path
from typing import Any

from coding_assistant.tools.errors import ApprovalRequiredError, ToolExecutionError
from coding_assistant.tools.paths import ALLOWED_TEST_COMMANDS, APPROVAL_ACTION_TYPES, resolve_workspace_path
from coding_assistant.tools.registry import get_registered_tool

_resolve_workspace_path = resolve_workspace_path

__all__ = [
    "ALLOWED_TEST_COMMANDS",
    "APPROVAL_ACTION_TYPES",
    "ApprovalRequiredError",
    "HANDLERS",
    "ToolExecutionError",
    "_resolve_workspace_path",
    "execute_registered_tool",
    "handle_apply_patch",
    "handle_approval_request",
    "handle_grep",
    "handle_lint",
    "handle_read_file",
    "handle_run_tests",
    "handle_search_code",
]


async def execute_registered_tool(
    tool_name: str,
    workspace_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    tool = get_registered_tool(tool_name)
    if tool is None:
        raise ToolExecutionError(f"Unknown tool: {tool_name}")
    return await tool.execute(workspace_root, args)


async def handle_read_file(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("read_file", workspace_root, args)


async def handle_grep(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("grep", workspace_root, args)


async def handle_search_code(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("search_code", workspace_root, args)


async def handle_apply_patch(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("apply_patch", workspace_root, args)


async def handle_run_tests(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("run_tests", workspace_root, args)


async def handle_lint(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("lint", workspace_root, args)


async def handle_approval_request(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("approval_request", workspace_root, args)


async def handle_mcp_invoke(workspace_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return await execute_registered_tool("mcp_invoke", workspace_root, args)


HANDLERS = {
    "read_file": handle_read_file,
    "grep": handle_grep,
    "search_code": handle_search_code,
    "apply_patch": handle_apply_patch,
    "run_tests": handle_run_tests,
    "lint": handle_lint,
    "approval_request": handle_approval_request,
    "mcp_invoke": handle_mcp_invoke,
}
