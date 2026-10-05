from coding_assistant.tools.base import RegisteredTool
from coding_assistant.config import get_settings
from coding_assistant.tools.builtin import (
    apply_patch_handler,
    approval_request_handler,
    grep_handler,
    lint_handler,
    mcp_invoke_handler,
    read_file_handler,
    run_tests_handler,
    search_code_handler,
)
from coding_assistant.tools.schemas import (
    ApplyPatchInput,
    ApprovalRequestInput,
    GrepInput,
    LintInput,
    McpInvokeInput,
    ReadFileInput,
    RunTestsInput,
    SearchCodeInput,
    ToolDefinition,
    ToolName,
)
from coding_assistant.tools.outputs import (
    ApplyPatchOutput,
    ApprovalRequestOutput,
    GrepOutput,
    LintOutput,
    McpInvokeOutput,
    ReadFileOutput,
    RunTestsOutput,
    SearchCodeOutput,
)

REGISTERED_TOOLS: dict[ToolName, RegisteredTool] = {
    "read_file": RegisteredTool(
        name="read_file",
        description="Read a file from the workspace (read-only).",
        input_model=ReadFileInput,
        output_model=ReadFileOutput,
        handler=read_file_handler,
    ),
    "grep": RegisteredTool(
        name="grep",
        description="Search file contents with a regex pattern.",
        input_model=GrepInput,
        output_model=GrepOutput,
        handler=grep_handler,
    ),
    "search_code": RegisteredTool(
        name="search_code",
        description="Semantic + symbol search via Tree-sitter index and pgvector (auto-indexes on first use).",
        input_model=SearchCodeInput,
        output_model=SearchCodeOutput,
        handler=search_code_handler,
    ),
    "apply_patch": RegisteredTool(
        name="apply_patch",
        description="Write full file content after host validation (deterministic apply).",
        input_model=ApplyPatchInput,
        output_model=ApplyPatchOutput,
        handler=apply_patch_handler,
    ),
    "run_tests": RegisteredTool(
        name="run_tests",
        description="Run allowlisted test commands in Docker sandbox (network off by default).",
        input_model=RunTestsInput,
        output_model=RunTestsOutput,
        handler=run_tests_handler,
    ),
    "lint": RegisteredTool(
        name="lint",
        description="Syntax-check Python files under the given paths.",
        input_model=LintInput,
        output_model=LintOutput,
        handler=lint_handler,
    ),
    "approval_request": RegisteredTool(
        name="approval_request",
        description="Request human approval for a sensitive action.",
        input_model=ApprovalRequestInput,
        output_model=ApprovalRequestOutput,
        handler=approval_request_handler,
    ),
    "mcp_invoke": RegisteredTool(
        name="mcp_invoke",
        description="Invoke a curated MCP connector (GitHub, Linear, Slack, etc.). Writes need approval.",
        input_model=McpInvokeInput,
        output_model=McpInvokeOutput,
        handler=mcp_invoke_handler,
    ),
}


def _iter_tools():
    for name, tool in REGISTERED_TOOLS.items():
        if name == "mcp_invoke" and not get_settings().mcp_agent_tools_enabled:
            continue
        yield tool


def get_registered_tool(name: str) -> RegisteredTool | None:
    if name in REGISTERED_TOOLS:
        return REGISTERED_TOOLS[name]  # type: ignore[index]
    return None


def list_tools() -> list[ToolDefinition]:
    return [tool.definition() for tool in _iter_tools()]


def get_tool(name: str) -> ToolDefinition | None:
    tool = get_registered_tool(name)
    return tool.definition() if tool else None


def tool_names() -> list[str]:
    return [tool.name for tool in _iter_tools()]


def openai_tool_specs() -> list[dict]:
    """LiteLLM / OpenAI function-calling compatible tool list."""
    specs = []
    for definition in list_tools():
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.input_schema,
                },
            }
        )
    return specs
