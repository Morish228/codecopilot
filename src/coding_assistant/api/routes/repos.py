from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.api.deps import db_session
from coding_assistant.intelligence.indexer import RepositoryIndexer

router = APIRouter(prefix="/v1/repos", tags=["repos"])


class IndexRepoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_root: str = Field(min_length=1)


class IndexRepoResponse(BaseModel):
    workspace_root: str
    file_count: int
    symbol_count: int
    indexed_at: str


@router.post("/index", response_model=IndexRepoResponse)
async def index_repo(
    body: IndexRepoRequest,
    session: AsyncSession = Depends(db_session),
) -> IndexRepoResponse:
    root = Path(body.workspace_root)
    if not root.is_dir():
        raise HTTPException(status_code=400, detail="workspace_root must be an existing directory")

    indexer = RepositoryIndexer(session)
    ws = await indexer.index_workspace(root)
    return IndexRepoResponse(
        workspace_root=ws.workspace_root,
        file_count=ws.file_count,
        symbol_count=ws.symbol_count,
        indexed_at=ws.indexed_at.isoformat(),
    )
