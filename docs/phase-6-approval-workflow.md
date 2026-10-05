# Phase 6 — Approval Workflow

**Status:** Complete  
**Date:** 2026-06-03

## Flow

```text
Tool call → policy / handler → PendingApproval + deferred_action
         → DB approval_requests + checkpoint
         → User POST .../approvals/{id} {approved: true}
         → Replay deferred_action (bypass_approval)
         → Resume LangGraph loop
```

## Persisted state

| Store | Contents |
| ----- | -------- |
| `agent_runs.state_snapshot` | Full graph state |
| `run_checkpoints` | Step history (`planner`, `awaiting_approval`, `post_approval_execute`, …) |
| `approval_requests` | action_type, payload, deferred_action, status |
| `run_messages` / `tool_calls` | Audit trail |

## Policy (`approval/policy.py`)

Requires approval for: `rm`, `git_reset`, `git_push`, package installs, network/env changes, non-allowlisted test commands, and `approval_request` for sensitive types.

## API

| Method | Path |
| ------ | ---- |
| GET | `/v1/runs/{id}/approvals` |
| GET | `/v1/runs/{id}/approvals/{approval_id}` |
| POST | `/v1/runs/{id}/approvals/{approval_id}` |
| GET | `/v1/runs/{id}/checkpoints` |

## Next: Phase 7

OpenTelemetry + Langfuse tracing.
