from coding_assistant.mcp.types import McpConnectorInfo

# Small curated catalog — expand deliberately per procedure.
CONNECTORS: dict[str, McpConnectorInfo] = {
    "github": McpConnectorInfo(
        name="github",
        category="development",
        description="GitHub issues and pull requests (read-first; writes need approval).",
        tools=["list_issues", "get_issue", "create_issue", "create_comment"],
        requires_approval_tools=["create_issue", "create_comment"],
    ),
    "gitlab": McpConnectorInfo(
        name="gitlab",
        category="development",
        description="GitLab issues and merge requests.",
        tools=["list_issues", "get_issue"],
        requires_approval_tools=[],
    ),
    "linear": McpConnectorInfo(
        name="linear",
        category="project_management",
        description="Linear issues and projects.",
        tools=["list_issues", "get_issue", "create_issue"],
        requires_approval_tools=["create_issue"],
    ),
    "jira": McpConnectorInfo(
        name="jira",
        category="project_management",
        description="Jira tickets.",
        tools=["search_issues", "get_issue"],
        requires_approval_tools=[],
    ),
    "notion": McpConnectorInfo(
        name="notion",
        category="knowledge",
        description="Notion pages (read-first).",
        tools=["search_pages", "get_page"],
        requires_approval_tools=["update_page"],
    ),
    "slack": McpConnectorInfo(
        name="slack",
        category="communication",
        description="Slack messages (posting requires approval).",
        tools=["list_channels", "post_message"],
        requires_approval_tools=["post_message"],
    ),
    "discord": McpConnectorInfo(
        name="discord",
        category="communication",
        description="Discord channels (posting requires approval).",
        tools=["list_channels", "post_message"],
        requires_approval_tools=["post_message"],
    ),
}


def list_connectors() -> list[McpConnectorInfo]:
    return list(CONNECTORS.values())


def get_connector(name: str) -> McpConnectorInfo | None:
    return CONNECTORS.get(name)
