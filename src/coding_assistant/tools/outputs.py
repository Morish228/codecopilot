"""Deterministic tool output models — serialized in stable field order."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReadFileOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    content: str
    lines: int


class GrepMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    line: int
    text: str


class GrepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    match_count: int
    matches: list[GrepMatch]


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    snippet: str
    kind: str = "unknown"
    name: str = ""
    score: float = 0.0


class SearchCodeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    hit_count: int
    hits: list[SearchHit]


class ApplyPatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    bytes_written: int


class RunTestsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    command: str
    workspace: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    sandbox: str
    message: str | None = None


class LintIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    line: int | None = None
    column: int | None = None
    code: str
    message: str


class LintOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    issue_count: int
    issues: list[LintIssue]


class ApprovalRequestOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    action_type: str
    reason: str


class McpInvokeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: str
    tool: str
    success: bool
    output: dict | None = None
    error: str | None = None


def serialize_output(model: BaseModel) -> dict[str, Any]:
    """Canonical JSON-serializable dict for tool results."""
    return model.model_dump(mode="json")
