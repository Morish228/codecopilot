import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.control_deps import AuthContext, get_optional_auth, get_project_for_org
from coding_assistant.api.deps import db_session
from coding_assistant.control_plane.audit import write_audit
from coding_assistant.control_plane.budget import BudgetExceeded, check_org_budgets, record_usage
from coding_assistant.control_plane.rate_limit import RateLimitExceeded, check_rate_limit
from coding_assistant.api.schemas import (
    ApprovalDecisionRequest,
    ApprovalResponse,
    CheckpointResponse,
    CreateRunRequest,
    RunResponse,
)
from coding_assistant.config import get_settings
from coding_assistant.db.models import RunStatus
from coding_assistant.runtime.approval_manager import ApprovalManager
from coding_assistant.runtime.graph import AgentRuntime
from coding_assistant.runtime.state_manager import StateManager
from coding_assistant.services.run_worker import execute_run_background, resume_run_background

router = APIRouter(prefix="/v1/runs", tags=["runs"])


def _to_run_response(run) -> RunResponse:
    return RunResponse(
        id=run.id,
        workspace_root=run.workspace_root,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        user_message=run.user_message,
        final_response=run.final_response,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("", response_model=RunResponse, status_code=202)
async def create_run(
    body: CreateRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_session),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> RunResponse:
    if auth and auth.organization:
        try:
            await check_rate_limit(str(auth.organization.id))
            await check_org_budgets(session, auth.organization)
        except RateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except BudgetExceeded as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc

    project_id = body.project_id
    if project_id and auth and auth.organization:
        await get_project_for_org(project_id, auth.organization.id, session)

    state_manager = StateManager(session)
    run = await state_manager.create_run(body.workspace_root, body.message, project_id=project_id)
    run.status = RunStatus.RUNNING
    await session.commit()
    await session.refresh(run)

    if auth and auth.organization:
        await record_usage(
            session,
            organization_id=auth.organization.id,
            project_id=project_id,
            run_id=run.id,
        )
        await write_audit(
            session,
            organization_id=auth.organization.id,
            user_id=auth.user.id,
            action="run.create",
            resource_type="run",
            resource_id=str(run.id),
        )

    settings = get_settings()
    background_tasks.add_task(
        execute_run_background,
        run.id,
        body.workspace_root,
        body.message,
        settings.max_agent_iterations,
    )
    return _to_run_response(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(db_session),
) -> RunResponse:
    state_manager = StateManager(session)
    run = await state_manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_response(run)


@router.get("/{run_id}/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(db_session),
) -> list[ApprovalResponse]:
    approval_manager = ApprovalManager(session)
    records = await approval_manager.list_pending(run_id)
    return [
        ApprovalResponse(
            id=r.id,
            run_id=r.run_id,
            action_type=r.action_type,
            payload=r.payload,
            status=r.status.value,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/{run_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(db_session),
) -> list[CheckpointResponse]:
    state_manager = StateManager(session)
    run = await state_manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = await state_manager.list_checkpoints(run_id)
    return [
        CheckpointResponse(
            id=r.id,
            run_id=r.run_id,
            step=r.step,
            approval_id=r.approval_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{run_id}/approvals/{approval_id}", response_model=RunResponse)
async def decide_approval(
    run_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_session),
) -> RunResponse:
    state_manager = StateManager(session)
    approval_manager = ApprovalManager(session)
    run = await state_manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    pending = await approval_manager.get_pending(run_id, approval_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Pending approval not found")

    background_tasks.add_task(resume_run_background, run_id, approval_id, body.approved)

    run.status = RunStatus.AWAITING_APPROVAL
    await session.commit()
    await session.refresh(run)
    return _to_run_response(run)


@router.get("/{run_id}/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    run_id: uuid.UUID,
    approval_id: uuid.UUID,
    session: AsyncSession = Depends(db_session),
) -> ApprovalResponse:
    from sqlalchemy import select
    from coding_assistant.db.models import ApprovalRequest

    result = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.run_id == run_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return ApprovalResponse(
        id=record.id,
        run_id=record.run_id,
        action_type=record.action_type,
        payload=record.payload,
        status=record.status.value,
        created_at=record.created_at,
    )
