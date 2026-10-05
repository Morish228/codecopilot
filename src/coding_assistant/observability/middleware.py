import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from coding_assistant.observability.metrics import record_http
from coding_assistant.observability.tracing import get_tracer, set_span_attributes


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == "/metrics":
            return await call_next(request)

        method = request.method
        tracer = get_tracer()
        started = time.perf_counter()

        with tracer.start_as_current_span(f"HTTP {method} {path}") as span:
            set_span_attributes(
                span,
                {
                    "http.method": method,
                    "http.route": path,
                    "http.url": str(request.url),
                },
            )
            response = await call_next(request)
            duration = time.perf_counter() - started
            span.set_attribute("http.status_code", response.status_code)
            record_http(method, _metric_path(path), response.status_code, duration)
            return response


def _metric_path(path: str) -> str:
    """Collapse UUID segments for lower Prometheus cardinality."""
    parts = path.split("/")
    normalized = []
    for part in parts:
        if len(part) == 36 and part.count("-") == 4:
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized) or "/"
