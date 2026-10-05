import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.control_deps import AuthContext, require_auth, require_org_admin
from coding_assistant.api.deps import db_session
from coding_assistant.control_plane.audit import write_audit
from coding_assistant.db.models import AuditLog, Organization, Policy, Project, UsageRecord

router = APIRouter(prefix="/v1/orgs", tags=["organizations"])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str


class PolicyUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: dict = Field(default_factory=dict)


class UsageSummary(BaseModel):
    organization_id: uuid.UUID
    runs_this_month: int
    cost_usd_this_month: float
    monthly_run_limit: int | None
    monthly_budget_usd: float | None


@router.get("/{org_id}/usage", response_model=UsageSummary)
async def org_usage(
    org_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    session: AsyncSession = Depends(db_session),
) -> UsageSummary:
    org = await _get_org(org_id, auth, session)
    start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from coding_assistant.db.models import AgentRun

    runs = await session.execute(
        select(func.count(AgentRun.id))
        .join(Project, AgentRun.project_id == Project.id)
        .where(Project.organization_id == org.id, AgentRun.created_at >= start)
    )
    cost = await session.execute(
        select(func.coalesce(func.sum(UsageRecord.cost_usd), 0)).where(
            UsageRecord.organization_id == org.id,
            UsageRecord.recorded_at >= start,
        )
    )
    return UsageSummary(
        organization_id=org.id,
        runs_this_month=runs.scalar() or 0,
        cost_usd_this_month=float(cost.scalar() or 0),
        monthly_run_limit=org.monthly_run_limit,
        monthly_budget_usd=org.monthly_budget_usd,
    )


@router.get("/{org_id}/audit-logs")
async def list_audit_logs(
    org_id: uuid.UUID,
    limit: int = 50,
    auth: AuthContext = Depends(require_auth),
    session: AsyncSession = Depends(db_session),
) -> list[dict]:
    await _get_org(org_id, auth, session)
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 200))
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/{org_id}/projects", response_model=ProjectResponse)
async def create_project(
    org_id: uuid.UUID,
    body: ProjectCreate,
    auth: AuthContext = Depends(require_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ProjectResponse:
    org = await _get_org(org_id, auth, session)
    slug = body.slug or body.name.lower().replace(" ", "-")
    project = Project(organization_id=org.id, name=body.name, slug=slug)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    await write_audit(
        session,
        organization_id=org.id,
        user_id=auth.user.id,
        action="project.create",
        resource_type="project",
        resource_id=str(project.id),
    )
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        slug=project.slug,
    )


@router.get("/{org_id}/projects", response_model=list[ProjectResponse])
async def list_projects(
    org_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    session: AsyncSession = Depends(db_session),
) -> list[ProjectResponse]:
    await _get_org(org_id, auth, session)
    result = await session.execute(select(Project).where(Project.organization_id == org_id))
    return [
        ProjectResponse(
            id=p.id,
            organization_id=p.organization_id,
            name=p.name,
            slug=p.slug,
        )
        for p in result.scalars().all()
    ]


@router.put("/{org_id}/policies/{key}")
async def upsert_policy(
    org_id: uuid.UUID,
    key: str,
    body: PolicyUpsert,
    auth: AuthContext = Depends(require_org_admin),
    session: AsyncSession = Depends(db_session),
) -> dict:
    org = await _get_org(org_id, auth, session)
    result = await session.execute(
        select(Policy).where(Policy.organization_id == org.id, Policy.key == key)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = Policy(organization_id=org.id, key=key, value=body.value)
        session.add(policy)
    else:
        policy.value = body.value
    await session.commit()
    await write_audit(
        session,
        organization_id=org.id,
        user_id=auth.user.id,
        action="policy.upsert",
        resource_type="policy",
        resource_id=key,
        metadata={"value": body.value},
    )
    return {"key": key, "value": policy.value}


async def _get_org(org_id: uuid.UUID, auth: AuthContext, session: AsyncSession) -> Organization:
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if auth.organization and auth.organization.id != org_id:
        raise HTTPException(status_code=403, detail="Wrong organization context")
    return org
