"""OpenTelemetry tracing helpers."""

from contextlib import asynccontextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

_tracer_name = "coding_assistant"


def get_tracer():
    return trace.get_tracer(_tracer_name)


def set_span_attributes(span, attributes: dict[str, Any] | None) -> None:
    if not attributes or span is None:
        return
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


@asynccontextmanager
async def traced_span(name: str, attributes: dict[str, Any] | None = None):
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        set_span_attributes(span, attributes)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
