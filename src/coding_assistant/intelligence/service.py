from pathlib import Path

from coding_assistant.config import get_settings
from coding_assistant.db.session import _get_engine
from coding_assistant.intelligence.indexer import RepositoryIndexer
from coding_assistant.intelligence.retriever import RepositoryRetriever, SearchHit


async def index_workspace(workspace_root: Path):
    _, factory = _get_engine()
    assert factory is not None
    async with factory() as session:
        indexer = RepositoryIndexer(session)
        return await indexer.index_workspace(workspace_root)


async def search_repository(
    workspace_root: Path,
    query: str,
    file_pattern: str | None = None,
) -> list[SearchHit]:
    settings = get_settings()
    _, factory = _get_engine()
    assert factory is not None
    from coding_assistant.observability.tracing import traced_span

    async with factory() as session:
        retriever = RepositoryRetriever(session)
        root = workspace_root.resolve()
        async with traced_span("retrieval.vector_search", {"query": query}):
            if settings.repo_auto_index and not await retriever.is_indexed(root):
                await RepositoryIndexer(session).index_workspace(root)
            return await retriever.search(root, query, file_pattern)


def fallback_text_search(
    workspace_root: Path,
    query: str,
    file_pattern: str | None,
) -> list[SearchHit]:
    """Used when DB/pgvector unavailable."""
    q = query.lower()
    root = workspace_root.resolve()
    glob = f"**/{file_pattern}" if file_pattern else "**/*"
    hits: list[SearchHit] = []
    for file_path in root.glob(glob):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if q in text.lower():
            hits.append(
                SearchHit(
                    path=str(file_path.relative_to(root)),
                    snippet=text[:300],
                    kind="file",
                    name=file_path.name,
                    score=0.0,
                )
            )
        if len(hits) >= 25:
            break
    return hits
