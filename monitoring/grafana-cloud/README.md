# Grafana Cloud production dashboard

`dashboard.json` is a starter dashboard for the golden signals (request
rate, 5xx error rate, p95/p99 latency) per production service, sourced from
the OTLP metrics exported by `shared/observability/__init__.py` (see
[`docs/observability/GRAFANA_CLOUD_PRODUCTION.md`](../../docs/observability/GRAFANA_CLOUD_PRODUCTION.md)).

## Importing

Grafana Cloud → Dashboards → New → Import → upload `dashboard.json` (or
paste its contents) → pick the stack's Prometheus/Mimir data source for the
`Metrics source` variable prompt.

## Metric names are unverified against a live stack

The queries assume the OpenTelemetry Python FastAPI instrumentor's default
(pre-semconv-1.23) HTTP server duration histogram —
`http.server.duration` (unit `ms`) — translates to Prometheus-style
`http_server_duration_milliseconds_{count,bucket}` on ingestion, with
`service.name` mapped to the `job` label (Grafana Cloud's documented OTLP
resource-attribute-to-label mapping). This repo has not yet sent real
traffic to a provisioned Grafana Cloud stack to confirm those exact names.

Before trusting this dashboard: send a few requests to each service, open
Explore → Metrics in Grafana Cloud, and search for `http_server_duration`
(or whatever prefix actually shows up). If the real metric/label names
differ, fix them here — panel `targets[].expr` in `dashboard.json` — and
re-export.
