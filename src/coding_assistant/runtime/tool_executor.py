import logging
from pathlib import Path

from coding_assistant.approval.policy import action_type_for_tool, requires_approval
from coding_assistant.observability.metrics import record_tool
from coding_assistant.observability.tracing import traced_span
from coding_assistant.runtime.types import AgentGraphState, PendingApproval, StructuredAction, ToolResult
from coding_assistant.tools.errors import ApprovalRequiredError, ToolExecutionError
from coding_assistant.tools.registry import get_registered_tool
from coding_assistant.tools.validation import ToolValidationError, validate_tool_arguments

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Validates structured actions against JSON Schema, then executes registered tools."""

    async def execute_actions(
        self,
        state: AgentGraphState,
        actions: list[StructuredAction],
        *,
        bypass_approval: bool = False,
    ) -> tuple[list[ToolResult], AgentGraphState]:
        workspace = Path(state["workspace_root"])
        results: list[ToolResult] = []
        updated = dict(state)

        for action in actions:
            result, updated = await self._execute_one(
                workspace, updated, action, bypass_approval=bypass_approval
            )
            results.append(result)
            if updated.get("pending_approval") and not bypass_approval:
                break

        updated["tool_results"] = list(state.get("tool_results") or []) + results
        return results, updated  # type: ignore[return-value]

    async def _execute_one(
        self,
        workspace: Path,
        state: AgentGraphState,
        action: StructuredAction,
        *,
        bypass_approval: bool = False,
    ) -> tuple[ToolResult, AgentGraphState]:
        tool_name = action.tool
        arguments = action.arguments

        tool = get_registered_tool(tool_name)
        if tool is None:
            return (
                ToolResult(
                    tool=tool_name,
                    arguments=arguments,
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                ),
                state,
            )

        if not bypass_approval:
            predicted = action_type_for_tool(tool_name, arguments)
            if predicted and requires_approval(predicted):
                return self._request_approval(
                    state, action, predicted, {"reason": "policy", "arguments": arguments}
                )

        try:
            from coding_assistant.approval.context import with_approval_bypass

            async with traced_span(
                f"tool.{tool_name}",
                {"tool.name": tool_name, "run.id": state.get("run_id")},
            ):
                ctx = with_approval_bypass() if bypass_approval else _null_context()
                with ctx:
                    validate_tool_arguments(tool_name, arguments)
                    output = await tool.execute(workspace, arguments)
            record_tool(tool_name, True)
            return (
                ToolResult(tool=tool_name, arguments=arguments, success=True, output=output),
                state,
            )
        except ToolValidationError as exc:
            record_tool(tool_name, False)
            return (
                ToolResult(
                    tool=tool_name,
                    arguments=arguments,
                    success=False,
                    error=str(exc),
                ),
                state,
            )
        except ApprovalRequiredError as exc:
            record_tool(tool_name, False)
            if bypass_approval:
                return (
                    ToolResult(
                        tool=tool_name,
                        arguments=arguments,
                        success=False,
                        error=f"Approved action still failed: {exc}",
                    ),
                    state,
                )
            return self._request_approval(state, action, exc.action_type, exc.payload)
        except ToolExecutionError as exc:
            record_tool(tool_name, False)
            return (
                ToolResult(
                    tool=tool_name,
                    arguments=arguments,
                    success=False,
                    error=str(exc),
                ),
                state,
            )
        except Exception as exc:
            record_tool(tool_name, False)
            logger.exception("Tool execution failed: %s", tool_name)
            return (
                ToolResult(
                    tool=tool_name,
                    arguments=arguments,
                    success=False,
                    error=str(exc),
                ),
                state,
            )

    def _request_approval(
        self,
        state: AgentGraphState,
        action: StructuredAction,
        action_type: str,
        payload: dict,
    ) -> tuple[ToolResult, AgentGraphState]:
        pending = PendingApproval(
            approval_id="",
            action_type=action_type,
            payload=payload,
            deferred_action=action,
        )
        new_state: AgentGraphState = {
            **state,
            "pending_approval": pending,
            "status": "awaiting_approval",
        }
        return (
            ToolResult(
                tool=action.tool,
                arguments=action.arguments,
                success=False,
                error=f"Approval required: {action_type}",
                output={"action_type": action_type, "payload": payload},
            ),
            new_state,
        )


class _null_context:
    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False
