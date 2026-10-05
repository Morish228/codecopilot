#!/usr/bin/env bash
# Create one git commit per completed phase (run from repo root).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -d .git ]]; then
  echo "Repository already initialized. Remove .git first if you want a clean phased history."
  exit 1
fi

git init -b main

git_add() {
  git add -A "$@" 2>/dev/null || true
}

# Phase 0 — product definition
git_add \
  procedure.md plan.md product.contract.json \
  docs/phase-0-product-definition.md
git commit -m "$(cat <<'EOF'
Define the product contract and scope for the coding assistant

Lock in what the CLI and control plane own, which capabilities ship in the
MVP, and which actions stay behind explicit approval. This gives us a shared
reference before any runtime code lands.
EOF
)"

# Phase 1 — core runtime
git_add \
  .gitignore pyproject.toml docker-compose.yml README.md .env.example \
  docs/phase-1-core-runtime.md \
  tests/test_graph.py tests/test_tools.py \
  src/coding_assistant/__init__.py src/coding_assistant/__main__.py \
  src/coding_assistant/config.py src/coding_assistant/app.py \
  src/coding_assistant/api/ \
  src/coding_assistant/db/ \
  src/coding_assistant/runtime/ \
  src/coding_assistant/services/ \
  src/coding_assistant/tools/
git reset HEAD src/coding_assistant/api/routes/repos.py 2>/dev/null || true
git reset HEAD src/coding_assistant/api/routes/routing.py 2>/dev/null || true
git reset HEAD src/coding_assistant/api/routes/metrics_route.py 2>/dev/null || true
git reset HEAD src/coding_assistant/api/routes/evals.py 2>/dev/null || true
git commit -m "$(cat <<'EOF'
Add the core agent runtime with FastAPI and LangGraph

Stand up the orchestration loop (planner, tool executor, state manager),
PostgreSQL and Redis persistence, and structured tool calls instead of raw
shell. Includes the hosted API skeleton for starting and inspecting runs.
EOF
)"

# Phase 2 — model routing
git_add \
  routing.config.json docs/phase-2-model-routing.md \
  tests/test_routing.py \
  src/coding_assistant/routing/ \
  src/coding_assistant/api/routes/routing.py
git commit -m "$(cat <<'EOF'
Route LLM calls by capability instead of hardcoding a single model

Introduce LiteLLM-backed routing with fast, reasoning, and coding tiers plus
fallback chains. The planner now asks for a capability and complexity, not a
provider string.
EOF
)"

# Phase 3 — tool system
git_add \
  docs/phase-3-tool-system.md tests/test_tool_system.py \
  src/coding_assistant/tools/base.py \
  src/coding_assistant/tools/schema_builder.py \
  src/coding_assistant/tools/validation.py \
  src/coding_assistant/tools/builtin.py \
  src/coding_assistant/tools/outputs.py \
  src/coding_assistant/tools/paths.py \
  src/coding_assistant/tools/errors.py
git commit -m "$(cat <<'EOF'
Harden tools with strict JSON Schema and deterministic outputs

Every tool now has validated inputs, forbidden extra fields, and typed
results. Host validation runs before execution so bad LLM payloads never reach
handlers.
EOF
)"

# Phase 4 — sandbox
git_add \
  Dockerfile.sandbox docs/phase-4-sandbox.md tests/test_sandbox.py \
  src/coding_assistant/sandbox/
git commit -m "$(cat <<'EOF'
Run tests inside Docker with network disabled by default

Replace the run_tests stub with a sandbox manager that maps allowlisted
commands to fixed argv and applies CPU, memory, and timeout limits in an
isolated container.
EOF
)"

# Phase 5 — repository intelligence
git_add \
  docs/phase-5-repository-intelligence.md tests/test_intelligence.py \
  src/coding_assistant/intelligence/ \
  src/coding_assistant/api/routes/repos.py \
  docker-compose.yml
git commit -m "$(cat <<'EOF'
Index Python symbols and add semantic code search

Parse repos with Tree-sitter, embed symbols into pgvector, and wire search_code
to the retriever. Adds an index API and switches Postgres to the pgvector image.
EOF
)"

# Phase 6 — approval workflow
git_add \
  docs/phase-6-approval-workflow.md tests/test_approval.py \
  src/coding_assistant/approval/
git commit -m "$(cat <<'EOF'
Pause risky actions for human approval and resume with replay

Centralize approval policy, persist checkpoints, store deferred tool actions,
and replay them after the user approves. Rejections fail the run cleanly
without half-applied side effects.
EOF
)"

# Phase 7 — observability
git_add \
  docs/phase-7-observability.md tests/test_observability.py tests/conftest.py \
  src/coding_assistant/observability/ \
  src/coding_assistant/api/routes/metrics_route.py
git commit -m "$(cat <<'EOF'
Add OpenTelemetry traces, Prometheus metrics, and Langfuse hooks

Instrument HTTP, agent steps, tool calls, and LLM completions. Expose a
/metrics endpoint for scraping and optional Langfuse logging when keys are set.
EOF
)"

# Phase 8 — evaluation
git_add \
  docs/phase-8-evaluation.md tests/test_evals.py \
  evals/ \
  src/coding_assistant/evals/ \
  src/coding_assistant/api/routes/evals.py \
  src/coding_assistant/api/router.py \
  README.md
git commit -m "$(cat <<'EOF'
Add a smoke evaluation harness for regression checks

Ship JSON datasets, fixture workspaces, and a runner that grades tool results
without calling the LLM. Exposes POST /v1/evals/run for CI-friendly smoke tests.
EOF
)"

# Anything left (shared file updates from later phases)
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "$(cat <<'EOF'
Wire remaining cross-phase integrations and README updates

Catch-all for shared modules updated across multiple phases (config, router,
handlers, planner) so the tree matches the final integrated system.
EOF
)"
fi

echo ""
git log --oneline
echo ""
echo "Done. $(git rev-list --count HEAD) commits on $(git branch --show-current)."
