from coding_assistant.mcp.registry import get_connector


def tool_requires_approval(connector: str, tool: str) -> bool:
    info = get_connector(connector)
    if info is None:
        return True
    if tool not in info.tools:
        return True
    return tool in info.requires_approval_tools


def approval_action_type(connector: str, tool: str) -> str:
    return f"mcp_{connector}_{tool}"
