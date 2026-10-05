"""Stub MCP backends for local dev and tests (no live server required)."""

from typing import Any


async def invoke_stub(connector: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if connector == "github" and tool == "list_issues":
        return {
            "issues": [
                {"number": 1, "title": "Example bug", "state": "open"},
                {"number": 2, "title": "Example feature", "state": "closed"},
            ],
            "repo": arguments.get("repo", "owner/name"),
        }
    if connector == "linear" and tool == "list_issues":
        return {"issues": [{"id": "LIN-1", "title": "Stub issue"}], "team": arguments.get("team", "ENG")}
    if connector == "slack" and tool == "list_channels":
        return {"channels": [{"id": "C001", "name": "general"}]}
    if tool in ("create_issue", "post_message", "create_comment", "update_page"):
        return {
            "status": "stub",
            "message": f"Would execute {connector}.{tool}",
            "arguments": arguments,
        }
    return {
        "status": "stub",
        "connector": connector,
        "tool": tool,
        "arguments": arguments,
    }
