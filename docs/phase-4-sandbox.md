# Phase 4 — Sandbox Execution

**Status:** Complete  
**Date:** 2026-06-03

## Goal

Run allowlisted test commands in an isolated environment with resource limits and network disabled by default.

## Architecture

```text
run_tests tool
      │
      ▼
SandboxManager
      │
      ├── DockerSandboxRunner (default)
      └── LocalSandboxRunner (SANDBOX_BACKEND=local, dev/tests)
      │
      ▼
Container / subprocess (fixed argv, no shell)
```

## Container restrictions (Docker)

| Control | Implementation |
| ------- | ---------------- |
| CPU | `--cpus` |
| Memory | `--memory` |
| Timeout | `asyncio.wait_for` on container run |
| Filesystem | Workspace mounted at `/workspace` only |
| Network | `--network none` by default (`SANDBOX_NETWORK_ENABLED=true` for bridge) |

## Allowlisted commands

Commands map to fixed argv (never `/bin/sh -c`):

| Command | argv |
| ------- | ---- |
| `pytest -q` | `pytest -q` |
| `pytest` | `pytest` |
| `python -m pytest -q` | `python -m pytest -q` |

Non-allowlisted commands raise `ApprovalRequiredError`.

## Setup

```bash
docker compose build sandbox-image
# or: docker build -f Dockerfile.sandbox -t coding-assistant-sandbox:local .
```

## Configuration

| Variable | Default |
| -------- | ------- |
| `SANDBOX_ENABLED` | `true` |
| `SANDBOX_BACKEND` | `docker` |
| `SANDBOX_IMAGE` | `coding-assistant-sandbox:local` |
| `SANDBOX_MEMORY_MB` | `512` |
| `SANDBOX_CPU_COUNT` | `1.0` |
| `SANDBOX_TIMEOUT_SECONDS` | `300` |
| `SANDBOX_NETWORK_ENABLED` | `false` |

Use `SANDBOX_BACKEND=local` when Docker is unavailable (dev only; no container isolation).

## Next: Phase 5

Repository indexing with Tree-sitter and pgvector.
