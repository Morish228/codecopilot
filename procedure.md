# Production-Grade Coding Assistant: Architecture, Build Plan, and Tech Stack

## Executive Summary

The recommended architecture is a **hybrid local CLI + hosted control plane** rather than a framework-heavy autonomous multi-agent system.

The local CLI owns:

* User interaction
* Repository access
* Approval workflows
* Local execution experience

The hosted control plane owns:

* Authentication
* Policy enforcement
* Telemetry
* Evaluations
* Model routing
* Usage tracking
* Budget enforcement

The primary design goals are:

1. Deterministic execution
2. Strong observability
3. Safe tool usage
4. Model provider flexibility
5. Production readiness

---

# High-Level Architecture

```text
┌─────────────────────┐
│      Local CLI      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Hosted API Layer   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│         Agent Runtime           │
│                                 │
│  ┌───────────────────────────┐  │
│  │      Model Router         │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │      Tool Registry        │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │    Approval Manager       │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │     State Manager         │  │
│  └───────────────────────────┘  │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Sandbox Executor   │
└─────────────────────┘
```

---

# Development Roadmap

## Phase 0 — Product Definition

### Supported Capabilities

* Repository inspection
* Code search
* Code explanation
* Refactoring
* Patch generation
* Test execution
* Documentation generation

### Explicitly Unsupported

* Automatic deployment
* Automatic Git push
* Arbitrary internet access
* Destructive commands without approval

---

# Phase 1 — Core Runtime

## Goal

Build the foundational orchestration system.

## Tech Stack

### Backend

* Python 3.12
* FastAPI
* Pydantic v2
* SQLAlchemy

### Storage

* PostgreSQL
* Redis

### Agent Framework

* LangGraph

### Model Access

* LiteLLM
* OpenAI SDK
* Anthropic SDK

---

## Runtime Architecture

```text
Agent Runtime
│
├── State Manager
├── Planner
├── Tool Executor
├── Approval Manager
└── Response Generator
```

### Important Principle

Never allow the LLM to directly execute shell commands.

Instead:

```text
LLM
 ↓
Structured Action
 ↓
Host Validation
 ↓
Execution
```

---

# Phase 2 — Model Routing Layer

## Goal

Decouple agents from specific model providers.

### Recommended Tool

LiteLLM

### Supported Providers

* OpenAI
* Anthropic
* Gemini
* OpenRouter
* Local Models

---

## Architecture

```text
Agent
  │
  ▼
Router
  │
  ├── Fast Models
  ├── Reasoning Models
  ├── Coding Models
  └── Fallback Models
```

---

## Example Routing Strategy

| Task           | Model Type             |
| -------------- | ---------------------- |
| File Search    | Small Fast Model       |
| Planning       | Strong Reasoning Model |
| Refactoring    | Strong Coding Model    |
| Debugging      | Reasoning Model        |
| Retry/Fallback | Cheap Model            |

---

## Design Rule

Agents should request capabilities:

```python
router.get_model(
    capability="planning",
    complexity="high"
)
```

Never hardcode:

```python
ChatOpenAI(...)
```

inside agent logic.

---

# Phase 3 — Tool System

## Goal

Build schema-driven tools.

### Example

```python
class SearchCode(BaseModel):
    query: str
    file_pattern: str | None
```

---

## Tool Registry

```text
Tool Registry
│
├── search_code
├── read_file
├── apply_patch
├── run_tests
├── lint
├── grep
└── approval_request
```

---

## Tool Requirements

Every tool must define:

```json
{
  "name": "...",
  "description": "...",
  "schema": {...}
}
```

Rules:

* Strict schemas
* Required fields
* additionalProperties = false
* Deterministic outputs

---

# Phase 4 — Sandbox Execution

## Goal

Prevent unsafe execution.

---

## Initial Choice

Docker

## Future Upgrade

Firecracker MicroVMs

---

## Architecture

```text
Agent
  │
  ▼
Sandbox Manager
  │
  ▼
Container
```

---

## Container Restrictions

### Resource Limits

* CPU quotas
* Memory quotas
* Execution timeout

### Filesystem Controls

* Isolated workspace
* Temporary storage
* Read-only secrets

### Network Controls

Default:

```text
Network Disabled
```

Enable only when required.

---

# Phase 5 — Repository Intelligence

## Goal

Provide repository understanding.

---

## Metadata Extraction

Store:

* Functions
* Classes
* Symbols
* Imports
* Dependencies
* Call relationships

---

## Technologies

### Parsing

Tree-sitter

### Embeddings

Embedding Model

### Vector Search

pgvector

---

## Retrieval Pipeline

```text
Repository
   │
   ▼
Indexer
   │
   ▼
Vector Store
   │
   ▼
Retriever
```

---

# Phase 6 — Approval Workflow

## Goal

Control side effects.

---

## Flow

```text
Agent
 ↓
Action Request
 ↓
Approval Queue
 ↓
User Decision
 ↓
Resume Execution
```

---

## Actions Requiring Approval

* rm
* git reset
* git push
* pip install
* npm install
* network access
* environment modifications

---

## Persisted State

Store:

* Messages
* Tool outputs
* Checkpoints
* Approval status
* Run metadata

---

# Phase 7 — Observability

## Goal

Make failures debuggable.

---

## Technologies

### Tracing

* OpenTelemetry
* Langfuse

### Metrics

* Prometheus
* Grafana

---

## Trace Structure

```text
Request
│
├── Planning
├── Retrieval
├── Tool Calls
├── Patch Application
├── Test Runs
└── Final Output
```

---

## Track Per Model Call

* Model
* Provider
* Cost
* Latency
* Input tokens
* Output tokens

---

# Phase 8 — Evaluation System

## Goal

Prevent regressions.

---

## Evaluation Categories

### Bug Fixing

```text
Input:
Bug report

Output:
Passing patch
```

### Refactoring

```text
Input:
Code

Output:
Improved implementation
```

### Test Generation

```text
Input:
Source file

Output:
Passing tests
```

---

## Metrics

* Success Rate
* Patch Accuracy
* Test Pass Rate
* Cost Per Task
* Latency

---

## Evaluation Architecture

```text
Dataset
   │
   ▼
Agent
   │
   ▼
Sandbox
   │
   ▼
Grader
```

---

# Phase 9 — Hosted Control Plane

## Goal

Provide SaaS infrastructure.

---

## Responsibilities

### Authentication

* OAuth
* JWT

### Organization Management

* Teams
* Projects
* Roles

### Usage Management

* Rate limits
* Budget limits
* Billing

### Governance

* Policies
* Audit logs
* Evaluation results

---

## Recommended Stack

### Backend

* FastAPI

### Database

* PostgreSQL

### Queue

* Redis
* Celery or Dramatiq

### Object Storage

* S3

---

# Phase 10 — MCP Ecosystem

## Goal

Provide external integrations.

Build only after:

* Tracing exists
* Approvals exist
* Sandbox exists
* Evals exist

---

## Example Integrations

### Development

* GitHub
* GitLab

### Project Management

* Jira
* Linear

### Knowledge

* Notion
* Confluence

### Communication

* Slack
* Discord

---

# Infrastructure Stack

## Backend

* Python 3.12
* FastAPI
* Pydantic v2
* SQLAlchemy

---

## Agent Runtime

* LangGraph
* LiteLLM

---

## Search

* Tree-sitter
* pgvector

---

## Database

* PostgreSQL

---

## Cache

* Redis

---

## Sandbox

### MVP

Docker

### Scale

Firecracker

---

## Observability

* OpenTelemetry
* Langfuse
* Prometheus
* Grafana

---

## Frontend

* Next.js
* TypeScript
* Tailwind
* shadcn/ui

---

## Infrastructure

### CI/CD

* GitHub Actions

### IaC

* Terraform

### Cloud

* AWS

### Storage

* S3

---

# Recommended Team Priorities

Effort allocation:

| Area                    | Effort |
| ----------------------- | ------ |
| Sandbox + Security      | 20%    |
| Observability           | 20%    |
| Evaluation System       | 20%    |
| Repository Intelligence | 15%    |
| Agent Runtime           | 15%    |
| UI                      | 10%    |

Most teams overinvest in agent orchestration and underinvest in evaluation, observability, and sandboxing. Production systems fail for operational reasons long before they fail because they need a more sophisticated planning agent.

---

# Key Architectural Decisions

## Keep Agents Simple

Avoid:

* Agent swarms
* Recursive planners
* Complex autonomous systems

until evaluation data demonstrates a measurable need.

---

## Prefer Deterministic Execution

Use:

```text
Model
    ↓
Structured Action
    ↓
Host Validation
    ↓
Execution
```

instead of allowing free-form command generation.

---

## Default to Safety

* Sandboxed execution
* Approval gates
* Network-denied environments
* Full audit logs

---

## Build Evals Early

Every prompt change, model change, or tool change should be evaluated before deployment.

---

# Final Recommendation

If building this today, the first production milestone would be:

1. Local CLI
2. LangGraph runtime
3. LiteLLM routing
4. Docker sandbox
5. Repository indexing with Tree-sitter + pgvector
6. Approval workflow
7. OpenTelemetry + Langfuse tracing
8. Evaluation harness

Only after these are stable would I build MCP integrations, hosted collaboration features, or multi-agent workflows.
