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

from unittest.mock import patch

import pytest

from shared.observability import init_observability


@pytest.fixture
def mocked_observability():
    with (
        patch("shared.observability.OTLPSpanExporter") as span_exporter,
        patch("shared.observability.OTLPMetricExporter") as metric_exporter,
        patch("shared.observability.SQLAlchemyInstrumentor"),
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

    def test_local_dev_defaults_to_the_http_otel_collector_port(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service")

        span_exporter.assert_called_once_with(endpoint="http://localhost:4318/v1/traces")
        metric_exporter.assert_called_once_with(endpoint="http://localhost:4318/v1/metrics")

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

    def test_explicit_endpoint_argument_overrides_env_var(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://should-not-be-used:4318")
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service", otlp_endpoint="http://explicit:4318")

        span_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/traces")
        metric_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/metrics")

    def test_trailing_slash_on_endpoint_does_not_double_up(
        self, monkeypatch, mocked_observability
    ):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        span_exporter, metric_exporter = mocked_observability

        init_observability("test-service", otlp_endpoint="http://explicit:4318/")

        span_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/traces")
        metric_exporter.assert_called_once_with(endpoint="http://explicit:4318/v1/metrics")
