from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolDefinition(BaseModel):
    """Public tool contract per Phase 3 procedure."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="schema")
    output_schema: dict[str, Any]

    @property
    def schema(self) -> dict[str, Any]:
        """Alias for procedure/docs compatibility."""
        return self.input_schema


# Backward-compatible alias
ToolSchema = ToolDefinition


class ReadFileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Relative path within the workspace")


class GrepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    path: str | None = Field(default=None, description="Optional subdirectory or file glob root")


class SearchCodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    file_pattern: str | None = None


class ApplyPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    content: str = Field(description="Full new file content after patch")


class RunTestsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(
        default="pytest -q",
        description="Test command; must be allowlisted by host validation",
    )


class LintInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)


class ApprovalRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class McpInvokeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


ToolName = Literal[
    "read_file",
    "grep",
    "search_code",
    "apply_patch",
    "run_tests",
    "lint",
    "approval_request",
    "mcp_invoke",
]
