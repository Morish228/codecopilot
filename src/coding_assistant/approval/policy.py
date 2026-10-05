"""Central approval policy — which actions require human consent."""

from typing import Any

from coding_assistant.tools.paths import APPROVAL_ACTION_TYPES

# Procedure Phase 6 list + tool-specific gates
REQUIRED_ACTION_TYPES = APPROVAL_ACTION_TYPES | frozenset(
    {
        "run_tests_non_allowlisted",
        "destructive_file_write",
    }
)


def requires_approval(action_type: str) -> bool:
    return action_type in REQUIRED_ACTION_TYPES or action_type.startswith("destructive_")


def action_type_for_tool(tool_name: str, arguments: dict[str, Any]) -> str | None:
    """Infer approval category from a structured tool call before execution."""
    if tool_name == "approval_request":
        action = str(arguments.get("action_type", ""))
        return action if requires_approval(action) else action or "approval_request"

    if tool_name == "run_tests":
        from coding_assistant.tools.paths import ALLOWED_TEST_COMMANDS

        cmd = arguments.get("command", "pytest -q")
        if cmd not in ALLOWED_TEST_COMMANDS:
            return "run_tests_non_allowlisted"

    if tool_name == "apply_patch":
        path = str(arguments.get("path", ""))
        if ".." in path:
            return "destructive_file_write"

    if tool_name == "mcp_invoke":
        from coding_assistant.mcp.policy import approval_action_type, tool_requires_approval

        connector = str(arguments.get("connector", ""))
        mcp_tool = str(arguments.get("tool", ""))
        if tool_requires_approval(connector, mcp_tool):
            return approval_action_type(connector, mcp_tool)

    return None
