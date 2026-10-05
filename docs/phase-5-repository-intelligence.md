# Phase 5 — Repository Intelligence

**Status:** Complete (MVP)  
**Date:** 2026-06-03

## Pipeline

```text
Workspace → Tree-sitter (Python symbols) → embeddings → pgvector
                                              ↓
                                    search_code / Retriever
```

## Stored metadata

- Functions, classes (name, kind, path, line range, snippet)
- Vector embedding per symbol (LiteLLM or deterministic offline fallback)

## API

```bash
curl -X POST http://127.0.0.1:8000/v1/repos/index \
  -H 'Content-Type: application/json' \
  -d '{"workspace_root": "/path/to/repo"}'
```

`search_code` auto-indexes on first use when `REPO_AUTO_INDEX=true`.

## Config

| Variable | Default |
| -------- | ------- |
| `EMBEDDING_MODEL` | unset (offline hash embeddings) |
| `EMBEDDING_DIMENSIONS` | `384` |
| `REPO_AUTO_INDEX` | `true` |
| `REPO_MAX_FILES` | `500` |

Postgres image: `pgvector/pgvector:pg16` (extension created on startup).

## Next: Phase 6

Approval workflow hardening and persisted resume state.
