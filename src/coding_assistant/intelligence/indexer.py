import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.config import get_settings
from coding_assistant.db.models import CodeSymbol, WorkspaceIndex
from coding_assistant.intelligence.embeddings import embed_texts
from coding_assistant.intelligence.parser import extract_python_symbols


class RepositoryIndexer:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    async def index_workspace(self, workspace_root: Path) -> WorkspaceIndex:
        root = workspace_root.resolve()
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")

        ws_key = str(root)
        result = await self._session.execute(
            select(WorkspaceIndex).where(WorkspaceIndex.workspace_root == ws_key)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            workspace = WorkspaceIndex(workspace_root=ws_key)
            self._session.add(workspace)
            await self._session.flush()

        await self._session.execute(delete(CodeSymbol).where(CodeSymbol.workspace_id == workspace.id))

        symbols = []
        file_count = 0
        for file_path in root.rglob("*.py"):
            if file_count >= self._settings.repo_max_files:
                break
            if any(part.startswith(".") for part in file_path.relative_to(root).parts):
                continue
            file_count += 1
            symbols.extend(extract_python_symbols(file_path, root))

        texts = [f"{s.kind} {s.name}\n{s.snippet}" for s in symbols]
        vectors = await embed_texts(texts) if texts else []

        for sym, vec in zip(symbols, vectors, strict=True):
            self._session.add(
                CodeSymbol(
                    id=uuid.uuid4(),
                    workspace_id=workspace.id,
                    path=sym.path,
                    kind=sym.kind,
                    name=sym.name,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    snippet=sym.snippet,
                    embedding=vec,
                )
            )

        workspace.file_count = file_count
        workspace.symbol_count = len(symbols)
        await self._session.commit()
        await self._session.refresh(workspace)
        return workspace
