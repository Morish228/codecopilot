# Phase 9 — Hosted Control Plane

**Status:** Complete (MVP)  
**Date:** 2026-06-03

## Capabilities

| Area | Implementation |
| ---- | -------------- |
| **Auth** | JWT (register, login, OAuth dev stub) |
| **Orgs & projects** | CRUD for projects, membership roles |
| **Usage** | Monthly run count + cost rollup |
| **Budgets** | Per-org monthly run limit and USD cap |
| **Rate limits** | Redis counter per org per minute |
| **Governance** | Policy key/value store, audit log |

## Auth endpoints

- `POST /v1/auth/register` — create user + org, returns JWT
- `POST /v1/auth/token` — email/password login
- `POST /v1/auth/oauth/callback` — dev OAuth stub (github/google)
- `GET /v1/auth/me` — current user context

Set `AUTH_REQUIRED=true` in production to enforce Bearer tokens on protected routes.

## Org endpoints

- `GET /v1/orgs/{id}/usage`
- `GET /v1/orgs/{id}/audit-logs`
- `GET/POST /v1/orgs/{id}/projects`
- `PUT /v1/orgs/{id}/policies/{key}`

Runs accept optional `project_id` and enforce budget/rate limits when authenticated.

## Next: Phase 10

MCP ecosystem integrations (after core loop is stable in production).
