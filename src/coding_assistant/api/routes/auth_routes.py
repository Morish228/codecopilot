import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.control_deps import AuthContext, require_auth
from coding_assistant.api.deps import db_session
from coding_assistant.control_plane.audit import write_audit
from coding_assistant.control_plane.auth import create_access_token, hash_password, verify_password
from coding_assistant.db.models import MemberRole, Organization, OrganizationMember, User

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=8)
    display_name: str
    organization_name: str


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    organization_id: uuid.UUID | None = None


class OAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(description="github | google (dev stub)")
    code: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    organization_id: uuid.UUID | None = None


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, session: AsyncSession = Depends(db_session)) -> TokenResponse:
    existing = await session.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    slug = _slugify(body.organization_name)
    org = Organization(name=body.organization_name, slug=slug, monthly_run_limit=1000, monthly_budget_usd=50.0)
    session.add(user)
    session.add(org)
    await session.flush()
    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.OWNER,
        )
    )
    await session.commit()

    token = create_access_token(user_id=user.id, org_id=org.id, role=MemberRole.OWNER.value)
    await write_audit(
        session,
        organization_id=org.id,
        user_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=str(user.id),
    )
    return TokenResponse(access_token=token, user_id=user.id, organization_id=org.id)


@router.post("/token", response_model=TokenResponse)
async def login(body: TokenRequest, session: AsyncSession = Depends(db_session)) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    org_id = body.organization_id
    role = MemberRole.MEMBER.value
    if org_id:
        member = await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == org_id,
            )
        )
        m = member.scalar_one_or_none()
        if m is None:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        role = m.role.value
    else:
        first = await session.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id).limit(1)
        )
        m = first.scalar_one_or_none()
        if m:
            org_id = m.organization_id
            role = m.role.value

    token = create_access_token(user_id=user.id, org_id=org_id, role=role)
    await write_audit(
        session,
        organization_id=org_id,
        user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
    )
    return TokenResponse(access_token=token, user_id=user.id, organization_id=org_id)


@router.post("/oauth/callback", response_model=TokenResponse)
async def oauth_callback(
    body: OAuthCallbackRequest,
    session: AsyncSession = Depends(db_session),
) -> TokenResponse:
    """Dev stub: trusts email + provider label instead of exchanging OAuth code."""
    if body.provider not in ("github", "google"):
        raise HTTPException(status_code=400, detail="Unsupported provider")

    result = await session.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=body.email.lower(),
            password_hash=hash_password(body.code),
            display_name=body.email.split("@")[0],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    member = await session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id).limit(1)
    )
    m = member.scalar_one_or_none()
    org_id = m.organization_id if m else None
    role = m.role.value if m else MemberRole.MEMBER.value
    token = create_access_token(user_id=user.id, org_id=org_id, role=role)
    return TokenResponse(access_token=token, user_id=user.id, organization_id=org_id)


@router.get("/me")
async def me(auth: AuthContext = Depends(require_auth)) -> dict:
    return {
        "user_id": str(auth.user.id),
        "email": auth.user.email,
        "display_name": auth.user.display_name,
        "organization_id": str(auth.organization.id) if auth.organization else None,
        "role": auth.role.value if auth.role else None,
    }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or str(uuid.uuid4())[:8]
