from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from coding_assistant.tools.schemas import ToolName


class StructuredAction(BaseModel):
    """LLM output: a single tool invocation — never raw shell."""

    model_config = ConfigDict(extra="forbid")

    tool: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thought: str = ""
    actions: list[StructuredAction] = Field(default_factory=list)
    finish: bool = False
    final_message: str | None = None


class ToolResult(BaseModel):
    tool: str
    arguments: dict[str, Any]
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None


class PendingApproval(BaseModel):
    approval_id: str
    action_type: str
    payload: dict[str, Any]
    deferred_action: StructuredAction | None = None


class AgentGraphState(TypedDict):
    run_id: str
    workspace_root: str
    user_message: str
    messages: Annotated[list[dict[str, str]], "conversation history"]
    iteration: int
    max_iterations: int
    planner_output: PlannerOutput | None
    tool_results: list[ToolResult]
    pending_approval: PendingApproval | None
    final_response: str | None
    status: Literal["running", "awaiting_approval", "completed", "failed"]
    error: str | None


def initial_state(
    run_id: str,
    workspace_root: str,
    user_message: str,
    max_iterations: int,
) -> AgentGraphState:
    return {
        "run_id": run_id,
        "workspace_root": workspace_root,
        "user_message": user_message,
        "messages": [{"role": "user", "content": user_message}],
        "iteration": 0,
        "max_iterations": max_iterations,
        "planner_output": None,
        "tool_results": [],
        "pending_approval": None,
        "final_response": None,
        "status": "running",
        "error": None,
    }
