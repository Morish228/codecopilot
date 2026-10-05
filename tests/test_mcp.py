import pytest

from coding_assistant.mcp.policy import tool_requires_approval
from coding_assistant.mcp.registry import list_connectors
from coding_assistant.mcp.runner import McpRunner


def test_connector_catalog():
    names = {c.name for c in list_connectors()}
    assert "github" in names
    assert "linear" in names
    assert "slack" in names


def test_write_tools_need_approval():
    assert tool_requires_approval("github", "create_issue")
    assert not tool_requires_approval("github", "list_issues")


@pytest.mark.asyncio
async def test_invoke_stub_github():
    runner = McpRunner()
    result = await runner.invoke("github", "list_issues", {"repo": "acme/app"})
    assert result.success
    assert result.output is not None
    assert "issues" in result.output


@pytest.mark.asyncio
async def test_invoke_write_blocked_without_bypass():
    runner = McpRunner()
    result = await runner.invoke("slack", "post_message", {"channel": "C1", "text": "hi"})
    assert result.approval_required
    assert not result.success


@pytest.mark.asyncio
async def test_invoke_write_with_bypass():
    runner = McpRunner(bypass_approval=True)
    result = await runner.invoke("slack", "post_message", {"channel": "C1", "text": "hi"})
    assert result.success
