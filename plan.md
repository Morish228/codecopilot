Grounded in OpenAI’s Responses/Structured Outputs/sandbox/guardrails/evals/production docs, Anthropic’s “Building effective agents,” OpenTelemetry, and MCP docs, the recommended shape is a hybrid local CLI + hosted control plane, not a big framework-heavy autonomous swarm.

**Plan**
1. Lock the product contract first: local CLI owns the user experience, repo access, and approval prompts; the hosted control plane owns auth, policy, telemetry, run storage, evals, routing, and budgets. Default to sandboxed execution with explicit approvals for destructive or sensitive actions.
2. Build one small orchestrator loop with a narrow tool surface: routing, repo inspection, patch proposal, test execution, and final synthesis. Use strict JSON-schema tool definitions, keep `additionalProperties: false`, require all fields, and defer rarely used tools rather than loading a giant catalog.
3. Make the execution boundary safe by design: run shell and file work in an isolated workspace or container, keep secrets in runtime config or secret stores, and log every tool request and result. Treat network access as off by default and only allow trusted destinations when the task truly needs it.
4. Make edits deterministic: the model proposes structured changes, the host applies them, and the host validates them with formatting, linting, type checks, and targeted tests before the run can continue. This keeps the model from directly “freehanding” risky shell behavior.
5. Add approvals and guardrails around side effects: confirm before deletes, installs, network-enabled commands, pushing changes, or anything outside the target repo. Use input guardrails to block bad requests early, tool guardrails near risky tools, and resumable state for approvals that require human review.
6. Treat observability as a core feature, not a bolt-on: emit traces for model calls, tool calls, approvals, handoffs, patch application, and test outcomes. Use those traces to debug individual runs first, then turn the same data into repeatable evals and regression suites.
7. Productionize with cost and latency controls: route simple tasks to smaller/faster models, reserve stronger models for planning and debugging, use prompt caching for stable prefixes, compaction for long runs, retries with exponential backoff, and background or WebSocket mode for long-running workflows. Add per-user and per-project spend limits, staging/prod separation, and canary rollouts.
8. Add MCP/connectors later, not first: use them only for trusted integrations once the core loop, approval model, and logging are stable. Prefer official or first-party servers, require approvals for sensitive tool use, and keep the imported tool set small.
9. Build a launch discipline: version prompts, schemas, and tool contracts; gate releases on trace reviews and evals; and keep rollback paths for model, prompt, and policy regressions. Improve prompts and tool design before reaching for fine-tuning or more autonomy.

**Production Focus**
The main production risks are unsafe shell access, prompt injection through external data, cost blowups from long agent loops, and silent quality regressions. The architecture above addresses those by separating control plane from execution plane, constraining tools, using approvals, and making trace/eval coverage mandatory before release.

**Relevant components**
- CLI entrypoint and interactive session manager.
- Agent runtime and orchestration layer.
- Structured tool schema layer for repo inspection, patching, testing, and approvals.
- Sandbox adapter for local and hosted execution.
- Hosted control plane for auth, tenancy, policy, telemetry, run storage, and evals.
- Trace, metrics, and log pipeline.
- Evaluation harness and regression dataset store.
- Optional MCP/connectors integration layer.

**Verification**
1. Build a scenario matrix that covers the core behaviors: read-only inspection, patch creation, test failure recovery, approval-gated commands, network-denied execution, and resume-from-state.
2. Run trace-based grading on representative coding tasks before each prompt, model, or tool-surface change.
3. Add integration tests that prove structured tool calls conform to schema, patch application is deterministic, and approvals block side effects until resumed.
4. Add sandbox tests that confirm network policy, secret handling, and filesystem isolation work as intended.
5. Add load and latency checks for long sessions, including compaction/resume, retry behavior, and streamed progress updates.
6. Add release gates for prompt/schema drift, cost per task, and regression in test-pass rate.

**Decisions**
- Use a hybrid architecture: local CLI for the user-facing experience plus a hosted control plane for auth, policy, telemetry, evals, and release management.
- Keep the agent design simple and composable; do not start with a multi-agent swarm or heavy framework abstraction unless evals show a measurable benefit.
- Prefer strict schema-based tool calls and deterministic host-side execution over free-form model-generated commands.
- Default to sandboxed execution with approvals for sensitive actions.
- Treat MCP/connectors as optional extensibility, not part of the core launch surface.

**Further Considerations**
1. Decide whether the hosted control plane should be single-tenant-by-default for teams or fully multi-tenant for a public SaaS launch. My recommendation is to start with single-tenant project isolation and graduate to broader tenancy later.
2. Decide whether the first public release should support remote MCP/connectors or only local sandboxed tools. My recommendation is to ship the core coding workflow first and add MCP after the trust, approval, and logging model is proven.