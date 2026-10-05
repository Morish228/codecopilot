import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.control_deps import AuthContext, require_auth
from coding_assistant.api.deps import db_session
from coding_assistant.control_plane.audit import write_audit
from coding_assistant.mcp.registry import list_connectors
from coding_assistant.mcp.runner import McpRunner
from coding_assistant.mcp.types import McpInvokeRequest, McpInvokeResult

router = APIRouter(prefix="/v1/mcp", tags=["mcp"])


@router.get("/connectors")
async def get_connectors(_auth: AuthContext = Depends(require_auth)) -> list[dict]:
    return [c.model_dump() for c in list_connectors()]


@router.post("/invoke", response_model=McpInvokeResult)
async def invoke_mcp(
    body: McpInvokeRequest,
    auth: AuthContext = Depends(require_auth),
    session: AsyncSession = Depends(db_session),
) -> McpInvokeResult:
    runner = McpRunner()
    result = await runner.invoke(
        body.connector,
        body.tool,
        body.arguments,
        run_id=body.run_id,
    )

    if auth.organization:
        await write_audit(
            session,
            organization_id=auth.organization.id,
            user_id=auth.user.id,
            action="mcp.invoke",
            resource_type="mcp",
            resource_id=f"{body.connector}.{body.tool}",
            metadata={
                "success": result.success,
                "approval_required": result.approval_required,
                "run_id": body.run_id,
            },
        )

    if result.approval_required:
        raise HTTPException(
            status_code=403,
            detail={
                "message": result.error,
                "approval_action_type": result.approval_action_type,
                "payload": result.output,
            },
        )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "MCP invoke failed")

    return result
