import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.db.models import AgentRun, RunCheckpoint, RunMessage, RunStatus, ToolCallRecord
from coding_assistant.runtime.types import AgentGraphState, ToolResult
from coding_assistant.util.sanitize import sanitize_for_storage
from coding_assistant.services.redis_client import cache_run_state, get_cached_run_state


class StateManager:
    """Persists run state to PostgreSQL and hot cache in Redis."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self,
        workspace_root: str,
        user_message: str,
        project_id: uuid.UUID | None = None,
    ) -> AgentRun:
        run = AgentRun(
            workspace_root=workspace_root,
            user_message=user_message,
            project_id=project_id,
            status=RunStatus.PENDING,
        )
        self._session.add(run)
        self._session.add(RunMessage(run=run, role="user", content=user_message))
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def get_run(self, run_id: uuid.UUID) -> AgentRun | None:
        result = await self._session.execute(select(AgentRun).where(AgentRun.id == run_id))
        return result.scalar_one_or_none()

    async def save_checkpoint(
        self,
        run_id: uuid.UUID,
        state: AgentGraphState,
        step: str,
        approval_id: uuid.UUID | None = None,
    ) -> RunCheckpoint:
        record = RunCheckpoint(
            run_id=run_id,
            step=step,
            state_snapshot=_state_to_snapshot(state),
            approval_id=approval_id,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def list_checkpoints(self, run_id: uuid.UUID, limit: int = 20) -> list[RunCheckpoint]:
        from sqlalchemy import desc

        result = await self._session.execute(
            select(RunCheckpoint)
            .where(RunCheckpoint.run_id == run_id)
            .order_by(desc(RunCheckpoint.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def persist_graph_state(
        self,
        run_id: str,
        state: AgentGraphState,
        *,
        checkpoint_step: str | None = None,
    ) -> None:
        await cache_run_state(run_id, dict(state))

        run = await self.get_run(uuid.UUID(run_id))
        if run is None:
            return

        run.state_snapshot = _state_to_snapshot(state)
        if state["status"] == "awaiting_approval":
            run.status = RunStatus.AWAITING_APPROVAL
        elif state["status"] == "completed":
            run.status = RunStatus.COMPLETED
            run.final_response = state.get("final_response")
        elif state["status"] == "failed":
            run.status = RunStatus.FAILED
            run.error = state.get("error")
        else:
            run.status = RunStatus.RUNNING

        await self._session.commit()

        if checkpoint_step:
            await self.save_checkpoint(uuid.UUID(run_id), state, checkpoint_step)

    async def load_graph_state(self, run_id: str) -> AgentGraphState | None:
        cached = await get_cached_run_state(run_id)
        if cached:
            return _snapshot_to_state(cached)

        run = await self.get_run(uuid.UUID(run_id))
        if run and run.state_snapshot:
            return _snapshot_to_state(run.state_snapshot)
        return None

    async def record_tool_call(self, run_id: uuid.UUID, result: ToolResult) -> None:
        record = ToolCallRecord(
            run_id=run_id,
            tool_name=result.tool,
            arguments=sanitize_for_storage(result.arguments),
            result=sanitize_for_storage(result.output),
            success=result.success,
        )
        self._session.add(record)
        await self._session.commit()

    async def append_message(self, run_id: uuid.UUID, role: str, content: str) -> None:
        self._session.add(RunMessage(run_id=run_id, role=role, content=content))
        await self._session.commit()


def _state_to_snapshot(state: AgentGraphState) -> dict[str, Any]:
    planner = state.get("planner_output")
    pending = state.get("pending_approval")
    return {
        "run_id": state["run_id"],
        "workspace_root": state["workspace_root"],
        "user_message": state["user_message"],
        "messages": state["messages"],
        "iteration": state["iteration"],
        "max_iterations": state["max_iterations"],
        "planner_output": planner.model_dump() if planner else None,
        "tool_results": [r.model_dump() for r in state["tool_results"]],
        "pending_approval": pending.model_dump() if pending else None,
        "final_response": state.get("final_response"),
        "status": state["status"],
        "error": state.get("error"),
    }


def _snapshot_to_state(snapshot: dict[str, Any]) -> AgentGraphState:
    from coding_assistant.runtime.types import PendingApproval, PlannerOutput

    planner_raw = snapshot.get("planner_output")
    pending_raw = snapshot.get("pending_approval")
    tool_results_raw = snapshot.get("tool_results") or []

    return {
        "run_id": snapshot["run_id"],
        "workspace_root": snapshot["workspace_root"],
        "user_message": snapshot["user_message"],
        "messages": snapshot["messages"],
        "iteration": snapshot["iteration"],
        "max_iterations": snapshot["max_iterations"],
        "planner_output": PlannerOutput.model_validate(planner_raw) if planner_raw else None,
        "tool_results": [ToolResult.model_validate(r) for r in tool_results_raw],
        "pending_approval": PendingApproval.model_validate(pending_raw) if pending_raw else None,
        "final_response": snapshot.get("final_response"),
        "status": snapshot["status"],
        "error": snapshot.get("error"),
    }
