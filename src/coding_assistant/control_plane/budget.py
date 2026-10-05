import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.db.models import AgentRun, Organization, Project, UsageRecord


class BudgetExceeded(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


async def check_org_budgets(session: AsyncSession, org: Organization) -> None:
    await check_run_budget(session, org)
    await check_cost_budget(session, org)


async def check_run_budget(session: AsyncSession, org: Organization) -> None:
    if org.monthly_run_limit is None:
        return

    start_of_month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    run_count_result = await session.execute(
        select(func.count(AgentRun.id))
        .join(Project, AgentRun.project_id == Project.id)
        .where(Project.organization_id == org.id, AgentRun.created_at >= start_of_month)
    )
    count = run_count_result.scalar() or 0
    if count >= org.monthly_run_limit:
        raise BudgetExceeded(f"Monthly run limit reached ({org.monthly_run_limit})")


async def check_cost_budget(session: AsyncSession, org: Organization) -> None:
    if org.monthly_budget_usd is None:
        return

    start_of_month = datetime.now(UTC).replace(day=1, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(UsageRecord.cost_usd), 0)).where(
            UsageRecord.organization_id == org.id,
            UsageRecord.recorded_at >= start_of_month,
        )
    )
    spent = float(result.scalar() or 0)
    if spent >= org.monthly_budget_usd:
        raise BudgetExceeded(f"Monthly budget exceeded (${org.monthly_budget_usd:.2f})")


async def record_usage(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID | None,
    run_id: uuid.UUID | None,
    cost_usd: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    session.add(
        UsageRecord(
            organization_id=organization_id,
            project_id=project_id,
            run_id=run_id,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )
    await session.commit()
