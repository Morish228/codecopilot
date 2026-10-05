import logging
import uuid
from typing import Any

from coding_assistant.config import get_settings
from coding_assistant.mcp.policy import approval_action_type, tool_requires_approval
from coding_assistant.mcp.registry import get_connector
from coding_assistant.mcp.stubs import invoke_stub
from coding_assistant.mcp.types import McpInvokeResult
from coding_assistant.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class McpRunner:
    """Invoke MCP connector tools with policy, tracing, and optional approval gate."""

    def __init__(self, *, bypass_approval: bool = False) -> None:
        self._bypass_approval = bypass_approval

    async def invoke(
        self,
        connector: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
    ) -> McpInvokeResult:
        settings = get_settings()
        if not settings.mcp_enabled:
            return McpInvokeResult(
                connector=connector,
                tool=tool,
                success=False,
                error="MCP integrations are disabled (MCP_ENABLED=false)",
            )

        info = get_connector(connector)
        if info is None:
            return McpInvokeResult(
                connector=connector,
                tool=tool,
                success=False,
                error=f"Unknown connector: {connector}",
            )

        if tool not in info.tools:
            return McpInvokeResult(
                connector=connector,
                tool=tool,
                success=False,
                error=f"Tool {tool!r} not in connector catalog",
            )

        args = arguments or {}
        if tool_requires_approval(connector, tool) and not self._bypass_approval:
            action = approval_action_type(connector, tool)
            return McpInvokeResult(
                connector=connector,
                tool=tool,
                success=False,
                approval_required=True,
                approval_action_type=action,
                output={"arguments": args, "approval_id": str(uuid.uuid4())},
                error=f"Approval required for {connector}.{tool}",
            )

        async with traced_span(
            "mcp.invoke",
            {
                "mcp.connector": connector,
                "mcp.tool": tool,
                "run.id": run_id,
            },
        ):
            try:
                output = await self._dispatch(connector, tool, args)
                return McpInvokeResult(
                    connector=connector,
                    tool=tool,
                    success=True,
                    output=output,
                )
            except Exception as exc:
                logger.exception("MCP invoke failed")
                return McpInvokeResult(
                    connector=connector,
                    tool=tool,
                    success=False,
                    error=str(exc),
                )

    async def _dispatch(self, connector: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        if settings.mcp_use_stubs:
            return await invoke_stub(connector, tool, arguments)

        # Live MCP via stdio when configured (optional per-connector env command).
        command = _connector_command(connector)
        if command:
            return await _invoke_stdio_mcp(command, connector, tool, arguments)

        return await invoke_stub(connector, tool, arguments)


def _connector_command(connector: str) -> list[str] | None:
    import os

    raw = os.environ.get(f"MCP_{connector.upper()}_COMMAND")
    if not raw:
        return None
    return raw.split()


async def _invoke_stdio_mcp(
    command: list[str],
    connector: str,
    tool: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Connect to an MCP server over stdio and call a tool (when mcp package + server available)."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise RuntimeError("mcp package not installed") from exc

    try:
        params = StdioServerParameters(command=command[0], args=command[1:])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                content = []
                for block in result.content:
                    text = getattr(block, "text", None)
                    if text:
                        content.append(text)
                return {"connector": connector, "tool": tool, "content": content}
    except Exception:
        logger.warning("stdio MCP failed for %s, falling back to stub", connector)
        return await invoke_stub(connector, tool, arguments)
