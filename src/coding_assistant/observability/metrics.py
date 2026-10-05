"""Prometheus metrics."""

from prometheus_client import Counter, Histogram, generate_latest

from coding_assistant.config import get_settings

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 30.0, 120.0),
)
RUNS_TOTAL = Counter("agent_runs_total", "Agent runs started", ["status"])
TOOL_CALLS = Counter("tool_calls_total", "Tool invocations", ["tool", "success"])
LLM_CALLS = Counter("llm_calls_total", "LLM completions", ["model", "status"])
LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 15.0, 60.0),
)
LLM_TOKENS = Counter("llm_tokens_total", "LLM tokens", ["model", "direction"])


def metrics_enabled() -> bool:
    return get_settings().metrics_enabled


def record_http(method: str, path: str, status: int, duration_s: float) -> None:
    if not metrics_enabled():
        return
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_LATENCY.labels(method=method, path=path).observe(duration_s)


def record_run_started() -> None:
    if metrics_enabled():
        RUNS_TOTAL.labels(status="started").inc()


def record_tool(tool: str, success: bool) -> None:
    if metrics_enabled():
        TOOL_CALLS.labels(tool=tool, success=str(success).lower()).inc()


def record_llm(model: str, status: str, duration_s: float, input_tokens: int | None, output_tokens: int | None) -> None:
    if not metrics_enabled():
        return
    LLM_CALLS.labels(model=model, status=status).inc()
    LLM_LATENCY.labels(model=model).observe(duration_s)
    if input_tokens:
        LLM_TOKENS.labels(model=model, direction="input").inc(input_tokens)
    if output_tokens:
        LLM_TOKENS.labels(model=model, direction="output").inc(output_tokens)


def render_metrics() -> bytes:
    return generate_latest()
