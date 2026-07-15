"""Shared observability setup using OTLP exporter for traces and metrics."""

import os
from functools import wraps

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response


def init_observability(service_name: str, otlp_endpoint: str | None = None):
    """Initialize OTLP-based observability for traces and metrics.

    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "localhost:4317")
                      Defaults to OTEL_EXPORTER_OTLP_ENDPOINT env var or "localhost:4317"
    """
    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in ("true", "1"):
        return

    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
        }
    )

    # Configure OTLP span exporter
    span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    # Configure OTLP metric exporter
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument SQLAlchemy globally
    SQLAlchemyInstrumentor().instrument()


def init_tracer_provider(
    service_name: str, jaeger_host: str = "localhost", jaeger_port: int = 6831
):
    """Deprecated: Use init_observability instead. Kept for backward compatibility."""
    otlp_endpoint = f"{jaeger_host}:{jaeger_port}"
    init_observability(service_name, otlp_endpoint)


def instrument_fastapi(app):
    """Instrument FastAPI app with tracing. Call this AFTER app is created."""
    FastAPIInstrumentor().instrument_app(app)


def traced(span_name: str | None = None):
    """Decorator to create a span for a function."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name or func.__name__):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual span creation."""
    return trace.get_tracer(name)


async def metrics_endpoint(_request):
    """Prometheus metrics endpoint for scraping by Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "init_observability",
    "init_tracer_provider",
    "instrument_fastapi",
    "traced",
    "get_tracer",
    "metrics_endpoint",
]
