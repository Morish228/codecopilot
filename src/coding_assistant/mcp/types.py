from pydantic import BaseModel, ConfigDict, Field


class McpConnectorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str
    description: str
    tools: list[str]
    requires_approval_tools: list[str] = Field(default_factory=list)


class McpInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: str
    tool: str
    arguments: dict = Field(default_factory=dict)
    run_id: str | None = None


class McpInvokeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: str
    tool: str
    success: bool
    output: dict | None = None
    error: str | None = None
    approval_required: bool = False
    approval_action_type: str | None = None
