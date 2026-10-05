import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from coding_assistant.config import get_settings

logger = logging.getLogger(__name__)
_initialized = False


def setup_observability() -> None:
    global _initialized
    if _initialized:
        return

    settings = get_settings()
    if settings.otel_enabled:
        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": "0.1.0",
            }
        )
        provider = TracerProvider(resource=resource)

        if settings.otel_exporter == "none":
            pass
        elif settings.otel_exporter == "console":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        elif settings.otel_exporter == "otlp":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
            except Exception as exc:
                logger.warning("OTLP exporter unavailable (%s), using console", exc)
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry enabled exporter=%s", settings.otel_exporter)

    _initialized = True
