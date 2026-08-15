"""Tests for shared/observability per grafana-cloud-free-tier-production tasks 1.3/1.4.

Exporter/provider construction is patched at the shared.observability module
level so these tests assert on what init_observability wires up, without
opening real HTTP connections or touching global OTel SDK state. TLS and
OTEL_EXPORTER_OTLP_HEADERS are read directly by the (mocked) exporters
themselves, from the endpoint scheme and env respectively — not reimplemented
here — so these tests only need to check the endpoint each exporter is
constructed with, including the "/v1/traces" / "/v1/metrics" suffix that
init_observability appends by hand (the exporters only auto-append it when
they fall back to reading OTEL_EXPORTER_OTLP_ENDPOINT themselves, which
doesn't happen when we pass an explicit endpoint= as done here).
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider as SDKLoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from shared.observability import init_logging, init_observability, set_span_attributes


@pytest.fixture
def mocked_observability():
    with (
        patch("shared.observability.OTLPSpanExporter") as span_exporter,
        patch("shared.observability.OTLPMetricExporter") as metric_exporter,
        # Lazily imported inside init_observability (see the httpx/pika
        # instrumentors below it), so it's patched at its own module rather
        # than as a shared.observability attribute.
        patch("opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor"),
        patch("shared.observability.TracerProvider"),
        patch("shared.observability.MeterProvider"),
        patch("shared.observability.trace"),
        patch("shared.observability.metrics"),
    ):
        yield span_exporter, metric_exporter


class TestInitObservability:
    def test_disabled_flag_short_circuits_before_any_exporter_is_built(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service")

        span_exporter.assert_not_called()
        metric_exporter.assert_not_called()

    def test_local_dev_lets_the_exporter_resolve_its_own_default(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service")

        # No override given, so endpoint=None is passed through — the real
        # exporter resolves this to its own "http://localhost:4318/..."
        # default (or per-signal OTEL_EXPORTER_OTLP_*_ENDPOINT, if set).
        span_exporter.assert_called_once_with(endpoint=None)
        metric_exporter.assert_called_once_with(endpoint=None)

    def test_blank_endpoint_env_var_is_treated_as_unset(self, monkeypatch, mocked_observability):
        # deploy.yml's envsubst turns an unset GitHub Actions secret into an
        # empty string, not an absent variable — this must not be forwarded
        # to the exporters as a schemeless "" endpoint.
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service")

        span_exporter.assert_called_once_with(endpoint=None)
        metric_exporter.assert_called_once_with(endpoint=None)
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in os.environ

    def test_grafana_cloud_endpoint_env_var_is_forwarded_as_is(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "https://otlp-gateway-prod-us-central-0.grafana.net/otlp",
        )
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service")

        span_exporter.assert_called_once_with(
            endpoint="https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces"
        )
        metric_exporter.assert_called_once_with(
            endpoint="https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/metrics"
        )

    def test_explicit_endpoint_argument_overrides_env_var(self, monkeypatch, mocked_observability):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://should-not-be-used:4318")
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service", otlp_endpoint="http://explicit:4318")

        span_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/traces")
        metric_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/metrics")

    def test_trailing_slash_on_endpoint_does_not_double_up(self, monkeypatch, mocked_observability):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service", otlp_endpoint="http://explicit:4318/")

        span_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/traces")
        metric_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/metrics")


@pytest.fixture
def mocked_logging():
    # Deliberately does NOT patch logging.getLogger — it's a stdlib module
    # object shared process-wide (including by pytest's own log capture), so
    # patching an attribute on it leaks far beyond this module. Instead, let
    # init_logging attach the mocked LoggingHandler to the real root logger,
    # and remove it again on teardown.
    with (
        patch("shared.observability.OTLPLogExporter") as log_exporter,
        patch("shared.observability.LoggerProvider"),
        patch("shared.observability.BatchLogRecordProcessor"),
        patch("shared.observability.set_logger_provider"),
        patch("shared.observability.LoggingHandler") as logging_handler,
    ):
        yield log_exporter, logging_handler

    root_logger = logging.getLogger()
    if logging_handler.return_value in root_logger.handlers:
        root_logger.removeHandler(logging_handler.return_value)


class TestInitLogging:
    def test_disabled_flag_short_circuits_before_any_exporter_is_built(
        self, monkeypatch, mocked_logging
    ):
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        log_exporter, logging_handler = mocked_logging

        init_logging("test-service")

        log_exporter.assert_not_called()
        logging_handler.assert_not_called()

    def test_local_dev_lets_the_exporter_resolve_its_own_default(self, monkeypatch, mocked_logging):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        log_exporter, *_ = mocked_logging

        init_logging("test-service")

        log_exporter.assert_called_once_with(endpoint=None)

    def test_grafana_cloud_endpoint_env_var_is_forwarded_with_logs_suffix(
        self, monkeypatch, mocked_logging
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "https://otlp-gateway-prod-us-central-0.grafana.net/otlp",
        )
        log_exporter, *_ = mocked_logging

        init_logging("test-service")

        log_exporter.assert_called_once_with(
            endpoint="https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/logs"
        )

    def test_blank_endpoint_env_var_is_treated_as_unset(self, monkeypatch, mocked_logging):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        log_exporter, *_ = mocked_logging

        init_logging("test-service")

        log_exporter.assert_called_once_with(endpoint=None)
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in os.environ

    def test_attaches_logging_handler_to_root_logger(self, monkeypatch, mocked_logging):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        _log_exporter, logging_handler = mocked_logging

        init_logging("test-service")

        assert logging_handler.return_value in logging.getLogger().handlers


class TestLogTraceCorrelation:
    def test_log_emitted_inside_active_span_carries_trace_and_span_ids(self):
        # Independent SDK provider instances (not the shared.observability
        # globals) so this doesn't mutate process-wide OTel state — this test
        # is verifying the SDK's own automatic log/trace correlation, not
        # init_logging's wiring (covered separately above).
        log_exporter = InMemoryLogExporter()
        logger_provider = SDKLoggerProvider(resource=Resource.create({"service.name": "test"}))
        logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

        span_exporter = InMemorySpanExporter()
        tracer_provider = SDKTracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
        tracer = tracer_provider.get_tracer("correlation-test")

        py_logger = logging.getLogger("shared-observability-correlation-test")
        py_logger.setLevel(logging.INFO)
        py_logger.addHandler(handler)
        py_logger.propagate = False
        try:
            with tracer.start_as_current_span("test-span") as span:
                span_context = span.get_span_context()
                py_logger.info("hello from inside span")
        finally:
            py_logger.removeHandler(handler)

        [record] = log_exporter.get_finished_logs()
        assert record.log_record.trace_id == span_context.trace_id
        assert record.log_record.span_id == span_context.span_id


class TestSetSpanAttributes:
    def test_stringifies_and_sets_each_attribute_on_the_current_span(self):
        mock_span = MagicMock()
        with patch("shared.observability.trace.get_current_span", return_value=mock_span):
            set_span_attributes(budget_id="abc-123", user_id="user-456")

        mock_span.set_attribute.assert_any_call("budget_id", "abc-123")
        mock_span.set_attribute.assert_any_call("user_id", "user-456")

    def test_stringifies_non_string_values(self):
        mock_span = MagicMock()
        with patch("shared.observability.trace.get_current_span", return_value=mock_span):
            set_span_attributes(count=42)

        mock_span.set_attribute.assert_called_once_with("count", "42")

    def test_skips_none_values(self):
        mock_span = MagicMock()
        with patch("shared.observability.trace.get_current_span", return_value=mock_span):
            set_span_attributes(budget_id="abc-123", user_id=None)

        mock_span.set_attribute.assert_called_once_with("budget_id", "abc-123")
