# Phase 0 — Product Definition

**Status:** Complete  
**Date:** 2026-06-03  
**Inputs:** [procedure.md](../procedure.md), [plan.md](../plan.md)

---

## 1. Product Summary

A **production-grade coding assistant** delivered as a **hybrid local CLI + hosted control plane**. The CLI is the primary interface for developers working in a repository; the control plane provides authentication, policy, telemetry, model routing, budgets, and run persistence.

**Positioning:** Deterministic, observable, and safe-by-default — not an autonomous multi-agent swarm. The model proposes structured actions; the host validates and executes them.

**First production milestone** (from procedure):

1. Local CLI  
2. LangGraph runtime  
3. LiteLLM routing  
4. Docker sandbox  
5. Repository indexing (Tree-sitter + pgvector)  
6. Approval workflow  
7. OpenTelemetry + Langfuse tracing  
8. Evaluation harness  

MCP integrations, hosted collaboration, and multi-agent workflows are **explicitly deferred** until the core loop is stable.

---

## 2. Architecture Contract

### 2.1 Local CLI owns

| Responsibility | Notes |
| ---------------- | ----- |
| User interaction | Prompts, streaming progress, session UX |
| Repository access | Read/write within user-selected workspace |
| Approval workflows | Present, collect, and resume human decisions |
| Local execution experience | Sandbox invocation, test output, diff preview |

### 2.2 Hosted control plane owns

| Responsibility | Notes |
| ---------------- | ----- |
| Authentication | OAuth, JWT |
| Policy enforcement | Org/project rules, tool allowlists |
| Telemetry | Traces, metrics, audit logs |
| Evaluations | Regression datasets, graders, release gates |
| Model routing | Capability-based selection via LiteLLM |
| Usage tracking | Tokens, cost, latency per call |
| Budget enforcement | Per-user and per-project limits |

### 2.3 Execution boundary (non-negotiable)

```text
LLM → Structured Action → Host Validation → Execution
```

The LLM **never** directly executes shell commands. All side effects pass through schema-validated tools and host checks.

### 2.4 Default safety posture

- Sandboxed execution (Docker for MVP)  
- Network **disabled** by default in sandbox  
- Approval gates for sensitive operations  
- Full audit logs for tool requests and results  

---

## 3. Supported Capabilities

Each capability below is **in scope** for the product. MVP indicates whether it ships in the first production milestone.

| Capability | Description | MVP | Host validation |
| ---------- | ----------- | --- | ----------------- |
| **Repository inspection** | List files, read contents, summarize structure, dependency hints | Yes | Read-only tools; workspace-bound paths |
| **Code search** | Text and semantic search over indexed repo | Yes | Scoped to workspace index |
| **Code explanation** | Answer questions about symbols, flows, and files | Yes | Read-only; cite sources |
| **Refactoring** | Propose and apply structured edits (rename, extract, move) | Yes | Patch host applies changes; lint/typecheck optional gate |
| **Patch generation** | Produce unified diffs or structured edit batches | Yes | Deterministic apply; no direct file writes from model |
| **Test execution** | Run configured test commands in sandbox | Yes | Allowlisted commands; timeout and resource limits |
| **Documentation generation** | Generate or update docs from code context | Yes | Same patch pipeline as code edits |

### 3.1 Primary user workflows

1. **Inspect** — “What does this module do?” / “Where is X used?”  
2. **Change** — “Refactor this function” / “Fix this bug” with patch + test loop  
3. **Verify** — Run tests and report pass/fail with traceable output  
4. **Document** — Generate README, API docs, or inline docstrings from source  

### 3.2 Personas (initial)

| Persona | Goal | Constraints |
| ------- | ---- | ----------- |
| **Individual developer** | Faster local coding tasks | Local CLI + optional cloud auth |
| **Team lead** | Policy, budgets, audit | Control plane policies and usage dashboards |
| **Platform engineer** | Safe rollout, evals before release | Eval harness + trace review gates |

---

## 4. Explicitly Unsupported

These are **out of product scope** unless explicitly revisited in a future phase. Enforcement is via policy, tool registry omission, and runtime denylists.

| Unsupported behavior | Rationale | Enforcement |
| -------------------- | --------- | ----------- |
| **Automatic deployment** | High blast radius; not a coding-loop concern | No deploy tools in registry; policy block |
| **Automatic Git push** | Requires credentials and irreversible remote effects | No `git push` without approval; default: not offered in MVP |
| **Arbitrary internet access** | Prompt injection and data exfiltration risk | Sandbox network off; egress allowlist only when approved |
| **Destructive commands without approval** | Prevents accidental data loss | Approval queue for rm, reset, install, env changes, etc. |

### 4.1 Deferred (not unsupported forever)

| Item | Defer until |
| ---- | ----------- |
| MCP / external connectors | Tracing, approvals, sandbox, evals stable |
| Multi-agent swarms | Eval data shows measurable benefit |
| Firecracker microVMs | Docker sandbox proven at scale |
| Full multi-tenant SaaS | Single-tenant project isolation proven first |

---

## 5. Approval Policy (product rules)

Actions that **require explicit user approval** before execution:

- `rm` and broad delete patterns  
- `git reset`, `git push`, force operations  
- `pip install`, `npm install`, and other package installs  
- Network-enabled commands or egress  
- Environment variable / config modifications outside sandbox temp  

Approval flow: Agent → Action Request → Approval Queue → User Decision → Resume Execution. State (messages, tool outputs, checkpoints, approval status) is persisted for resume.

---

## 6. Non-Functional Requirements

| Area | Requirement |
| ---- | ----------- |
| **Determinism** | Structured tool I/O; host-side patch apply; schema `additionalProperties: false` |
| **Observability** | Trace every model call, tool call, approval, patch, and test run |
| **Cost control** | Route by capability; per-run and per-project budgets |
| **Latency** | Fast models for search; strong models for planning/debugging |
| **Quality** | No prompt/model/tool change without eval regression check |
| **Tenancy (initial)** | Single-tenant-by-default project isolation; multi-tenant SaaS later |

---

## 7. MVP Tool Surface (contract preview)

Narrow tool catalog for Phase 1+; aligns with procedure Phase 3 registry:

- `search_code`  
- `read_file`  
- `apply_patch`  
- `run_tests`  
- `lint`  
- `grep`  
- `approval_request`  

Tools not in this list are not loaded in MVP unless added through versioned schema change + eval.

---

## 8. Success Criteria for Phase 0

Phase 0 is complete when:

- [x] Supported capabilities are enumerated with MVP and validation notes  
- [x] Unsupported behaviors are explicit with enforcement approach  
- [x] CLI vs control plane responsibilities are locked  
- [x] Execution boundary (structured action → host) is documented  
- [x] Approval policy for side effects is defined  
- [x] Deferred features are listed to prevent scope creep  
- [x] Machine-readable contract exists for downstream phases (`product.contract.json`)

---

## 9. Phase 1 Handoff

**Next phase:** [Phase 1 — Core Runtime](../procedure.md#phase-1--core-runtime)

Deliverables expected from Phase 1:

- Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy skeleton  
- LangGraph orchestrator with State Manager, Planner, Tool Executor, Approval Manager, Response Generator  
- PostgreSQL + Redis wiring  
- No direct shell execution from LLM  

Reference implementation principles remain in [plan.md](../plan.md) sections **Plan**, **Decisions**, and **Verification**.
