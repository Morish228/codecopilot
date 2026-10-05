# Phase 7 — Observability

**Status:** Complete  
**Date:** 2026-06-03

## Stack

| Layer | Tool |
| ----- | ---- |
| Tracing | OpenTelemetry (console / OTLP) |
| LLM audit | Langfuse (optional) |
| Metrics | Prometheus (`GET /metrics`) |

## Trace hierarchy

```text
HTTP request
└── agent.run
    ├── agent.planning → planning (LLM)
    ├── agent.tool_calls → tool.{name}
    │   └── retrieval.search_code (search_code)
    └── agent.final_output
```

## LLM attributes

Per completion: model, provider, latency, input/output tokens, cost (via LiteLLM).

## Config

| Variable | Default |
| -------- | ------- |
| `OTEL_ENABLED` | `true` |
| `OTEL_EXPORTER` | `console` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318/v1/traces` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | unset |
| `METRICS_ENABLED` | `true` |

## Endpoints

- `GET /metrics` — Prometheus scrape target
- Traces export to console (dev) or OTLP collector

## Next: Phase 8

Evaluation harness and regression datasets.
