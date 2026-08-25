"""Shared observability setup using OTLP exporter for traces, metrics, and logs."""

import inspect
import logging
import os
from functools import wraps

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response


def is_observability_disabled() -> bool:
    """Whether OTEL_SDK_DISABLED opts the current process out of all OTLP export."""
    return os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in ("true", "1")


def _resolve_base_endpoint(otlp_endpoint: str | None) -> str | None:
    """Resolve the base OTLP endpoint from an explicit arg or OTEL_EXPORTER_OTLP_ENDPOINT.

    Returns None when neither is set, so callers can pass endpoint=None to let
    each exporter resolve and suffix its own endpoint from env.
    """
    if otlp_endpoint is not None:
        return otlp_endpoint.rstrip("/")

    # envsubst turns an unset GitHub Actions secret into an empty string, not
    # an absent variable, so os.getenv's own default never fires here —
    # normalize "" to "unset" ourselves instead of leaking it to the
    # exporters (they have the same "" vs. unset blind spot).
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip() or None
    if not endpoint:
        os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
        return None
    return endpoint.rstrip("/")


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
    if is_observability_disabled():
        return

    base_endpoint = _resolve_base_endpoint(otlp_endpoint)

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
    if base_endpoint:
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

    # Auto-instrument SQLAlchemy globally — imported lazily and skipped where
    # it isn't installed (e.g. worker, which has no FastAPI/HTTP surface and
    # doesn't carry opentelemetry-instrumentation-sqlalchemy), same reasoning
    # as the httpx/pika instrumentors below.
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
    except ImportError:
        pass

    # Auto-instrument outbound httpx calls (inter-service HTTP) globally —
    # imported lazily and skipped where it isn't installed (e.g. chat-service,
    # which imports this module transitively via shared.security.dependencies
    # but has no reason to depend on opentelemetry-instrumentation-httpx),
    # rather than making it a hard dependency of every service that imports
    # anything from shared/observability or shared/security.
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

    # Auto-instrument pika (RabbitMQ) globally — same reasoning as httpx
    # above; only budget/users-service depend on the raw `pika` package.
    try:
        from opentelemetry.instrumentation.pika import PikaInstrumentor

        PikaInstrumentor().instrument()
    except ImportError:
        pass


def instrument_fastapi(app):
    """Instrument FastAPI app with tracing. Call this AFTER app is created."""
    # Imported lazily so non-HTTP consumers of this module (e.g. worker) don't
    # need fastapi / opentelemetry-instrumentation-fastapi installed just to
    # import shared.observability.
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor().instrument_app(app)


def init_logging(service_name: str, otlp_endpoint: str | None = None) -> None:
    """Attach an OTLP logging handler to the root `logging` logger.

    Mirrors init_observability's endpoint resolution (same env var, same
    "/v1/logs" suffixing) and OTEL_SDK_DISABLED bail-out, so logs follow the
    same enable/disable/endpoint rules as traces and metrics. Independent of
    init_observability — call both, in either order.

    Uses a BatchLogRecordProcessor (background export thread) so logging
    calls never block on network I/O to the OTLP gateway. Log records emitted
    while a span is active are automatically tagged with that span's
    trace_id/span_id by the SDK.
    """
    if is_observability_disabled():
        return

    base_endpoint = _resolve_base_endpoint(otlp_endpoint)
    log_endpoint = f"{base_endpoint}/v1/logs" if base_endpoint else None

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
        }
    )

    log_exporter = OTLPLogExporter(endpoint=log_endpoint)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)


def traced(span_name: str | None = None):
    """Decorator to create a span for a function. Works on sync and async functions."""

    def decorator(func):
        name = span_name or func.__name__

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(name):
                    return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name):
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
    "init_logging",
    "instrument_fastapi",
    "traced",
    "get_tracer",
    "set_span_attributes",
    "metrics_endpoint",
    "is_observability_disabled",
]
