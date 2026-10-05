# Phase 2 — Model Routing Layer

**Status:** Complete  
**Date:** 2026-06-03

## Goal

Decouple agents from specific model providers. Runtime code requests **capabilities**, not `ChatOpenAI(...)` or hardcoded model strings.

## Architecture

```text
Planner (agent)
      │
      ▼
infer_capability_and_complexity(state)
      │
      ▼
ModelRouter.get_model(capability, complexity)
      │
      ├── fast tier      → file_search
      ├── reasoning tier → planning, debugging
      ├── coding tier    → refactoring, coding
      └── fallback tier  → retries / failures
      │
      ▼
RoutedCompletionService → LiteLLM (with fallback_chain)
```

## Configuration

`routing.config.json` at project root (override with `ROUTING_CONFIG_PATH`):

- **tiers** — maps tier name → LiteLLM model id  
- **routes** — maps capability + complexity → tier  
- **fallback_chain** — models to try if primary fails  

Single-model dev mode: set `ROUTING_DEFAULT_MODEL` (or legacy `LITELLM_MODEL`) to override all tiers.

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/v1/routing` | Full routing table |
| GET | `/v1/routing/resolve?capability=planning&complexity=high` | Preview resolved model |

## Code map

| Module | Role |
| ------ | ---- |
| `routing/types.py` | `Capability`, `Complexity`, `ModelRoute` |
| `routing/router.py` | `ModelRouter.get_model()` |
| `routing/policy.py` | Infer capability from `AgentGraphState` |
| `routing/completion.py` | LiteLLM calls + fallback + usage metadata |
| `runtime/planner.py` | Uses router only (no direct model string) |

## Routing policy (heuristic)

| Signal | Capability | Complexity |
| ------ | ---------- | ---------- |
| First iteration | planning | high |
| Recent tool failures | fallback | low |
| User message / failed tests (debug terms) | debugging | high |
| Recent `apply_patch` / write tools | coding / refactoring | high |
| Recent read-only tools only | file_search | low |
| Default mid-loop | planning | medium |

## Supported providers (via LiteLLM)

OpenAI, Anthropic, **Gemini**, OpenRouter, and local models — any LiteLLM model id in `tiers` or `fallback_chain`.

### Gemini setup

| Env | Purpose |
| --- | ------- |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Google AI / Vertex key for LiteLLM |
| `ROUTING_CONFIG_PATH=routing.config.gemini.json` | Gemini-first tier map (optional) |
| `ROUTING_DEFAULT_MODEL=gemini/gemini-2.0-flash` | Single-model override (optional) |

Keys from `.env` are synced into the process environment on server startup (`routing/credentials.py`) so LiteLLM can authenticate without exporting variables manually.

## Next: Phase 3

Schema-driven tool system hardening (strict JSON Schema export, host validation polish).
