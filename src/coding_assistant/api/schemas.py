import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    message: str = Field(min_length=1)
    project_id: uuid.UUID | None = None


class RunResponse(BaseModel):
    id: uuid.UUID
    workspace_root: str
    status: str
    user_message: str
    final_response: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    action_type: str
    payload: dict[str, Any]
    status: str
    created_at: datetime


class CheckpointResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    step: str
    approval_id: uuid.UUID | None
    created_at: datetime


class ToolDefinitionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="schema", serialization_alias="schema")
    output_schema: dict[str, Any]
