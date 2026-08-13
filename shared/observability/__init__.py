"""Shared observability setup using OTLP exporter for traces and metrics."""

import os
from functools import wraps

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
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
        otlp_endpoint: Base OTLP/HTTP endpoint (e.g. "http://localhost:4318" or
                      "https://otlp-gateway-<region>.grafana.net/otlp"). Each
                      exporter appends its own "/v1/traces" or "/v1/metrics"
                      suffix. Defaults to OTEL_EXPORTER_OTLP_ENDPOINT env var,
                      falling back to each exporter's own default
                      ("http://localhost:4318") when that's unset or blank.

    Uses OTLP/HTTP (protobuf), not gRPC: Grafana Cloud's OTLP gateway does not
    accept gRPC on any region/hostname (its fronting proxy never negotiates
    ALPN for h2, so grpc-core refuses the TLS handshake before any request is
    sent — confirmed against the production gateway, not a local library
    issue). TLS and headers are entirely env-driven by the exporters
    themselves: TLS follows the endpoint's http/https scheme, and
    OTEL_EXPORTER_OTLP_HEADERS (e.g. "authorization=Basic <base64>") is read
    directly by each exporter when headers isn't passed explicitly. Local dev,
    which sets neither, is unaffected.
    """
    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in ("true", "1"):
        return

    if otlp_endpoint is None:
        # envsubst turns an unset GitHub Actions secret into an empty string,
        # not an absent variable, so os.getenv's own default never fires here
        # — normalize "" to "unset" ourselves instead of leaking it to the
        # exporters below (they have the same "" vs. unset blind spot).
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip() or None
        if not otlp_endpoint:
            os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
        }
    )

    # Only build an explicit endpoint when one was actually given (arg or
    # non-empty env var). Otherwise pass endpoint=None so each exporter
    # resolves and suffixes its own endpoint from env, honoring the
    # per-signal OTEL_EXPORTER_OTLP_TRACES_ENDPOINT / _METRICS_ENDPOINT
    # overrides and its own "http://localhost:4318" default.
    if otlp_endpoint:
        base_endpoint = otlp_endpoint.rstrip("/")
        trace_endpoint = f"{base_endpoint}/v1/traces"
        metric_endpoint = f"{base_endpoint}/v1/metrics"
    else:
        trace_endpoint = None
        metric_endpoint = None

    # Configure OTLP span exporter
    span_exporter = OTLPSpanExporter(endpoint=trace_endpoint)
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    # Configure OTLP metric exporter
    metric_exporter = OTLPMetricExporter(endpoint=metric_endpoint)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument SQLAlchemy globally
    SQLAlchemyInstrumentor().instrument()

    # Auto-instrument outbound httpx calls (inter-service HTTP) globally
    HTTPXClientInstrumentor().instrument()

    # Auto-instrument pika (RabbitMQ) globally — only budget/users-service
    # depend on the raw `pika` package (ai-service doesn't use RabbitMQ), so
    # this is imported lazily and skipped where it isn't installed rather
    # than making `opentelemetry-instrumentation-pika` a hard dependency of
    # every service that calls init_observability().
    try:
        from opentelemetry.instrumentation.pika import PikaInstrumentor

        PikaInstrumentor().instrument()
    except ImportError:
        pass


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


def set_span_attributes(**attributes) -> None:
    """Set one or more attributes on the currently active span.

    Values are stringified (span attributes must be primitives) and `None`
    values are skipped. Safe to call outside a request context — a no-op
    span silently ignores `set_attribute`.
    """
    span = trace.get_current_span()
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, str(value))


async def metrics_endpoint(_request):
    """Prometheus metrics endpoint for scraping by Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "init_observability",
    "instrument_fastapi",
    "traced",
    "get_tracer",
    "set_span_attributes",
    "metrics_endpoint",
]
