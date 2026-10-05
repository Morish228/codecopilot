# Phase 1 — Core Runtime

**Status:** Complete  
**Date:** 2026-06-03

## Delivered

| Component | Location | Role |
| --------- | -------- | ---- |
| **State Manager** | `runtime/state_manager.py` | PostgreSQL persistence + Redis hot cache |
| **Planner** | `runtime/planner.py` | LiteLLM → structured `PlannerOutput` (no shell) |
| **Tool Executor** | `runtime/tool_executor.py` | Schema validation + registered handlers |
| **Approval Manager** | `runtime/approval_manager.py` | Queue / resolve sensitive actions |
| **Response Generator** | `runtime/response_generator.py` | Final user message synthesis |
| **LangGraph** | `runtime/graph.py` | `planner → execute_tools → (loop|respond|interrupt)` |

## Execution model

```text
LLM (Planner)
  ↓ JSON PlannerOutput.actions[]
StructuredAction { tool, arguments }
  ↓ ToolExecutor + registry validation
Host handler (read_file, grep, …)
  ↓
ToolResult → loop or respond
```

The LLM never receives a shell execution path. `run_tests` only accepts allowlisted commands; non-allowlisted commands raise `ApprovalRequiredError`.

## API (hosted control plane stub)

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/health` | Liveness |
| GET | `/v1/tools` | Tool registry + JSON schemas |
| POST | `/v1/runs` | Start run (202, background execution) |
| GET | `/v1/runs/{id}` | Run status |
| GET | `/v1/runs/{id}/approvals` | Pending approvals |
| POST | `/v1/runs/{id}/approvals/{approval_id}` | Approve / reject and resume |

## Stack

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg  
- PostgreSQL + Redis (`docker-compose.yml`)  
- LangGraph state machine  
- LiteLLM for planner calls (routing layer expanded in Phase 2)

## Stubs (by design)

- `run_tests` — returns stub until Phase 4 Docker sandbox  
- `lint` — returns stub until Phase 3+ integration  
- `search_code` — text search only; pgvector in Phase 5  

## Next: Phase 2

Capability-based model routing via LiteLLM; remove hardcoded model from planner.
