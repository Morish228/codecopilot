from coding_assistant.observability.metrics import metrics_enabled, record_http, record_tool
from coding_assistant.observability.middleware import _metric_path
from coding_assistant.observability.setup import setup_observability
from coding_assistant.observability.tracing import get_tracer


def test_setup_observability_idempotent(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER", "none")
    from coding_assistant.observability import setup as setup_mod

    setup_mod._initialized = False
    setup_observability()
    setup_observability()
    assert get_tracer() is not None


def test_metric_path_normalizes_uuids():
    path = "/v1/runs/550e8400-e29b-41d4-a716-446655440000/approvals"
    assert "{id}" in _metric_path(path)


def test_record_metrics_no_crash(monkeypatch):
    monkeypatch.setenv("METRICS_ENABLED", "true")
    from coding_assistant.config import get_settings

    get_settings.cache_clear()
    assert metrics_enabled()
    record_http("GET", "/health", 200, 0.01)
    record_tool("grep", True)


def test_prometheus_render():
    from coding_assistant.observability.metrics import render_metrics

    body = render_metrics()
    assert b"http_requests_total" in body or len(body) > 0
