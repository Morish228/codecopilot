import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.db.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=metadata or {},
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry
