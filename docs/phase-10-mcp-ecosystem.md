# Phase 10 — MCP Ecosystem

**Status:** Complete (MVP)  
**Date:** 2026-06-03

## Goal

Optional external integrations behind the same approval, audit, and tracing model as core tools.

## Connectors (curated catalog)

| Category | Connectors |
| -------- | ---------- |
| Development | github, gitlab |
| Project management | linear, jira |
| Knowledge | notion |
| Communication | slack, discord |

Read-only tools run immediately. Writes (`create_issue`, `post_message`, etc.) return **approval required**.

## API

- `GET /v1/mcp/connectors` — catalog (auth required)
- `POST /v1/mcp/invoke` — run a connector tool

## Agent tool (optional)

Set `MCP_AGENT_TOOLS_ENABLED=true` to expose `mcp_invoke` to the planner. Default off to keep the core tool surface small.

## Configuration

| Variable | Default |
| -------- | ------- |
| `MCP_ENABLED` | `true` |
| `MCP_USE_STUBS` | `true` (stub backends for dev) |
| `MCP_AGENT_TOOLS_ENABLED` | `false` |
| `MCP_GITHUB_COMMAND` | optional stdio server command |

## Prerequisites met

Tracing, approvals, sandbox, and evals were completed in prior phases before enabling MCP.
