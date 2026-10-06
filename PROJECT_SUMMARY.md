# CodeCopilot — Project Summary

**An agentic coding assistant with a capability-aware LLM router, a sandboxed tool-execution runtime, human-in-the-loop approvals, and semantic repository search — exposed over an HTTP API, a CLI, and a web UI.**

Built in Python 3.12+ (FastAPI, LangGraph, LiteLLM, SQLAlchemy/asyncpg, pgvector, Redis, tree-sitter). Managed with `uv`. 64 passing tests.

---

## What it does

CodeCopilot takes a natural-language coding request against a target workspace and runs it through a **Plan → Act → Observe** agent loop until the task is done:

1. **Plan** — an LLM planner proposes the next tool action (schema-constrained JSON).
2. **Act** — the chosen tool runs; file-mutating or destructive actions are gated behind an approval step.
3. **Observe** — the result feeds back into state, and the loop continues or finishes.

Runs are persisted, resumable, and streamed to the client; approvals pause the run and resume it once a human decides.

## Architecture (8 wired subsystems)

| Layer | Implementation |
|---|---|
| **Agent runtime** | LangGraph state machine (`planner → tool_executor → response_generator`) with conditional edges and a persisted, resumable state. |
| **Model routing** | Capability- and complexity-aware router over LiteLLM: maps each step to a model tier (Gemini / OpenAI / Anthropic) with a fallback chain. Config-driven (`routing.config*.json`). |
| **Tool system** | 8 real tools (`read_file`, `grep`, `search_code`, `apply_patch`, `run_tests`, `lint`, `mcp_invoke`, `approval_request`) with JSON-Schema input/output validation. |
| **Sandbox** | Pluggable execution backend — real subprocess (local) or an isolated `docker run` container with network/memory/CPU limits, command allowlist, timeout, and output caps. |
| **Approval workflow** | Policy classifies each action; sensitive ones halt the graph into `awaiting_approval`, persist to DB, and resume with a bypass token once approved. |
| **Repository intelligence** | tree-sitter AST symbol extraction → embeddings → pgvector store; semantic search ranked by true cosine similarity with a keyword tiebreaker. |
| **Control plane** | JWT/bcrypt auth, per-org budget caps, Redis rate limiting, and an audit log. |
| **Observability** | OpenTelemetry tracing, Prometheus `/metrics`, optional Langfuse tracing — wired across the runtime and model calls. |

## Interfaces

- **HTTP API** — FastAPI control plane: `POST /v1/runs`, run/approval/checkpoint reads, `/health`, `/metrics`, repo indexing, routing/tool introspection.
- **CLI** — interactive REPL (`coding-assistant chat`) that creates runs, streams status, and handles approval prompts.
- **Web UI** — single-page chat client: set a workspace, submit tasks, watch runs, and approve/reject gated actions.

## Engineering highlights

- **Deterministic agent orchestration** via an explicit LangGraph state machine rather than ad-hoc prompt chaining — every transition (plan, act, approve, finish) is a typed node with persisted state.
- **Provider-agnostic model routing** — one capability request resolves to a concrete model + fallback chain, so the agent degrades gracefully instead of crashing when a provider/key is unavailable.
- **Defense-in-depth execution** — command allowlist, workspace-path containment (component-aware, no prefix-escape), container isolation, resource limits, and an approval gate for anything destructive.
- **Semantic + lexical code search** — pgvector cosine ranking fused with keyword boosting, with a filesystem text-search fallback when the DB is down.
- **Fully typed, tested, reproducible** — Pydantic models throughout, 64 unit tests, `uv.lock` for deterministic installs.

## Tech stack

`Python 3.12+` · `FastAPI` · `LangGraph` · `LiteLLM` · `SQLAlchemy (async) + asyncpg` · `PostgreSQL + pgvector` · `Redis` · `tree-sitter` · `Docker` · `OpenTelemetry` · `Prometheus` · `pytest` · `uv`

## Run it

```bash
uv sync --extra dev
# infra: Postgres(pgvector) + Redis
docker compose up -d postgres redis
# configure .env (DB/Redis URLs + one LLM key), then:
uv run python -m coding_assistant serve --port 8001   # http://127.0.0.1:8001  (/, /docs, /health)
uv run python -m coding_assistant chat --workspace .   # interactive CLI
```
