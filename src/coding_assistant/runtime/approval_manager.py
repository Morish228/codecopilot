import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.db.models import ApprovalRequest, ApprovalStatus, AgentRun, RunStatus
from coding_assistant.runtime.types import AgentGraphState, PendingApproval, StructuredAction


class ApprovalManager:
    """Queues and resolves human approval for sensitive actions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, run_id: uuid.UUID, pending: PendingApproval) -> ApprovalRequest:
        payload = dict(pending.payload)
        if pending.deferred_action:
            payload["deferred_action"] = pending.deferred_action.model_dump()

        record = ApprovalRequest(
            run_id=run_id,
            action_type=pending.action_type,
            payload=payload,
            status=ApprovalStatus.PENDING,
        )
        self._session.add(record)
        run = await self._session.get(AgentRun, run_id)
        if run:
            run.status = RunStatus.AWAITING_APPROVAL
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_pending(
        self,
        run_id: uuid.UUID,
        approval_id: uuid.UUID,
    ) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.run_id == run_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def resolve(
        self,
        approval_id: uuid.UUID,
        approved: bool,
    ) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        record.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        record.resolved_at = datetime.now(UTC)
        run = await self._session.get(AgentRun, record.run_id)
        if run:
            run.status = RunStatus.RUNNING if approved else RunStatus.FAILED
            if not approved:
                run.error = f"Approval rejected: {record.action_type}"
        await self._session.commit()
        await self._session.refresh(record)
        return record

    def deferred_action_from_pending(self, pending: PendingApproval | None) -> StructuredAction | None:
        if pending and pending.deferred_action:
            return pending.deferred_action
        return None

    def deferred_action_from_record(self, record: ApprovalRequest) -> StructuredAction | None:
        raw = record.payload.get("deferred_action")
        if raw:
            return StructuredAction.model_validate(raw)
        return None

    def clear_pending(self, state: AgentGraphState, approved: bool) -> AgentGraphState:
        if not approved:
            return {
                **state,
                "pending_approval": None,
                "status": "failed",
                "error": "User rejected approval",
                "final_response": "Action was rejected by the user.",
            }
        return {
            **state,
            "pending_approval": None,
            "status": "running",
        }

    async def list_pending(self, run_id: uuid.UUID) -> list[ApprovalRequest]:
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.run_id == run_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
        )
        return list(result.scalars().all())
