import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.deps import db_session
from coding_assistant.config import get_settings
from coding_assistant.control_plane.auth import decode_access_token
from coding_assistant.db.models import MemberRole, Organization, OrganizationMember, Project, User

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    organization: Organization | None
    role: MemberRole | None


async def get_optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(db_session),
) -> AuthContext | None:
    if credentials is None:
        return None
    return await _auth_from_token(credentials.credentials, session)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(db_session),
) -> AuthContext:
    settings = get_settings()
    if not settings.auth_required and credentials is None:
        return AuthContext(user=_dev_user(), organization=None, role=None)
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await _auth_from_token(credentials.credentials, session)


async def _auth_from_token(token: str, session: AsyncSession) -> AuthContext:
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    org = None
    role = None
    org_id_raw = payload.get("org_id")
    if org_id_raw:
        org_id = uuid.UUID(org_id_raw)
        org = await session.get(Organization, org_id)
        member = await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
        membership = member.scalar_one_or_none()
        if membership:
            role = membership.role

    return AuthContext(user=user, organization=org, role=role)


def _dev_user() -> User:
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="dev@local",
        password_hash="",
        display_name="Dev User",
    )


async def require_org_admin(auth: AuthContext = Depends(require_auth)) -> AuthContext:
    settings = get_settings()
    if auth.role is None and not settings.auth_required:
        return auth
    if auth.role not in (MemberRole.OWNER, MemberRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return auth


async def get_project_for_org(
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    session: AsyncSession,
) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
