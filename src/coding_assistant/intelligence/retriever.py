from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coding_assistant.db.models import CodeSymbol, WorkspaceIndex
from coding_assistant.intelligence.embeddings import embed_texts


class SearchHit:
    __slots__ = ("path", "snippet", "kind", "name", "score")

    def __init__(
        self,
        path: str,
        snippet: str,
        kind: str,
        name: str,
        score: float,
    ) -> None:
        self.path = path
        self.snippet = snippet
        self.kind = kind
        self.name = name
        self.score = score


class RepositoryRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_indexed(self, workspace_root: Path) -> bool:
        ws = await self._get_workspace(str(workspace_root.resolve()))
        return ws is not None and ws.symbol_count > 0

    async def search(
        self,
        workspace_root: Path,
        query: str,
        file_pattern: str | None = None,
        limit: int = 25,
    ) -> list[SearchHit]:
        ws = await self._get_workspace(str(workspace_root.resolve()))
        if ws is None or ws.symbol_count == 0:
            return []

        query_vec = (await embed_texts([query]))[0]
        stmt = select(CodeSymbol).where(CodeSymbol.workspace_id == ws.id)
        if file_pattern:
            stmt = stmt.where(CodeSymbol.path.like(f"%{file_pattern}%"))

        stmt = stmt.order_by(CodeSymbol.embedding.cosine_distance(query_vec)).limit(limit * 2)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        q = query.lower()
        hits: list[SearchHit] = []
        for row in rows:
            keyword_boost = 0.0
            if q in row.name.lower() or q in row.snippet.lower():
                keyword_boost = 0.15
            hits.append(
                SearchHit(
                    path=row.path,
                    snippet=row.snippet[:300],
                    kind=row.kind,
                    name=row.name,
                    score=keyword_boost,
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    async def _get_workspace(self, workspace_root: str) -> WorkspaceIndex | None:
        result = await self._session.execute(
            select(WorkspaceIndex).where(WorkspaceIndex.workspace_root == workspace_root)
        )
        return result.scalar_one_or_none()
