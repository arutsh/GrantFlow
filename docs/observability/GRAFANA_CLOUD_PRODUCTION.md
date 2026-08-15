# Production Observability — Grafana Cloud

Production traces, metrics, and logs are exported directly from each service
to a hosted Grafana Cloud free-tier stack. No collector, Jaeger, Prometheus,
or Grafana container runs on the production box — that stack (see
[MONITORING_SETUP.md](MONITORING_SETUP.md)) exists only in dev, where it was
already judged too heavy for the 4GB Hetzner server.

## How it works

All five production services — the four FastAPI services (`users`, `budget`,
`ai`, `chat`) and the Celery `worker` — call `init_observability(service_name)`
from `shared/observability/__init__.py` at startup, and `init_logging(service_name)`
alongside it (see [Logs](#logs) below). Both functions are entirely
config-driven — the call sites never change per environment:

- **Transport**: OTLP/HTTP (protobuf), not gRPC. Grafana Cloud's OTLP gateway
  does not accept gRPC at all, in any region — its fronting proxy is
  HTTP/1.1-only and never negotiates ALPN for `h2`, so a gRPC client's TLS
  handshake is refused before any request is sent. Confirmed both by testing
  directly against the production gateway and with Grafana support. `init_observability`
  appends `/v1/traces` / `/v1/metrics` to the base endpoint itself.
- **Endpoint**: `OTEL_EXPORTER_OTLP_ENDPOINT` — Grafana Cloud's OTLP gateway
  base URL for the provisioned stack, e.g.
  `https://otlp-gateway-prod-gb-south-1.grafana.net/otlp` (the exact hostname
  depends on the stack's region — find it under Connections → Collector
  Setup → OpenTelemetry, or the stack's Details page). Unset or pointed at
  `localhost:4318` (dev's default, the local OTel Collector's HTTP receiver
  port), traces/metrics go to the local OTel Collector exactly as before.
- **Auth**: `OTEL_EXPORTER_OTLP_HEADERS` — a Basic Auth header
  (`authorization=Basic <base64(instance_id:api_token)>`) issued by Grafana
  Cloud's access policy for the stack. Unset in dev, so no auth is sent
  locally. Note the value is `base64(instance_id:token)`, not the raw API
  token by itself — a raw token pasted in directly will authenticate as
  nothing and get a 401.
- **TLS**: derived automatically by the exporter from the endpoint's
  `http://` vs `https://` scheme — no separate flag needed.
- **Kill switch**: `OTEL_SDK_DISABLED=true` makes both `init_observability()`
  and `init_logging()` no-ops for that service — no exporters are
  constructed and no OTLP calls (traces, metrics, or logs) are made. This is
  the rollback path if the Grafana Cloud integration misbehaves; no code
  change or revert needed, just set the flag per service and redeploy.

## Worker instrumentation

The Celery `worker` service has no HTTP surface, so it doesn't get
FastAPI/SQLAlchemy auto-instrumentation. Instead, `services/worker/celery_app.py`
hand-wires three Celery signals (`task_prerun`, `task_postrun`, `task_failure`)
to:

- start a span per task execution (named after the task, e.g.
  `tasks.users.send_verification_email`), ending it on `task_postrun`;
- mark the span `ERROR` and call `record_exception()` on `task_failure`;
- increment a `worker.tasks` counter (Prometheus name `worker_tasks_total`
  after OTel's dot-to-underscore + `_total` suffix translation), labeled
  `task_name` and `status` (`success` / `failure`), in both the success and
  failure paths.

Signal handlers are only connected when telemetry is enabled — `OTEL_SDK_DISABLED=true`
skips `.connect()` entirely rather than connecting inert handlers.

## Logs

All five services attach an OTLP logging handler to the root `logging`
logger via `init_logging(service_name)`, shipping every `INFO`-and-above log
record — including framework-level logging like Celery's own task-failure
traceback — to Grafana Cloud Loki. This is what closes the original gap: a
worker task exception previously showed up nowhere but `docker logs` on the
production host.

- **Transport/endpoint/auth**: identical to traces/metrics — same
  `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_HEADERS`, with
  `init_logging` appending `/v1/logs` to the base endpoint itself.
- **Delivery**: batched via `BatchLogRecordProcessor` (background export
  thread), so logging calls never block on network I/O to the OTLP gateway.
- **Trace correlation**: a log record emitted while a span is active is
  automatically tagged with that span's `trace_id`/`span_id` by the SDK — no
  extra code needed at the call site. In Grafana, jump from a trace in
  Tempo to its correlated log lines, or from a log line's `trace_id` field
  back to the trace.
- **Worker-specific wiring**: Celery's own logging bootstrap
  (`worker_hijack_root_logger`, on by default) clears any handlers already
  on the root logger when the worker process starts, which would silently
  wipe a handler attached at plain import time. `celery_app.py` instead
  attaches the OTLP handler from an `after_setup_logger` signal handler,
  which fires *after* Celery's own bootstrap — so it lands alongside
  Celery's console handler instead of being discarded by it.

### Searching logs in Grafana

**Explore → Loki**, filtering by service:

```logql
{service_name="worker"}
```

(`service_name="users-service"` / `"budget-service"` / `"ai-service"` /
`"chat-service"` for the other four). To pivot from a trace to its logs, copy
the trace ID from Tempo and search `{service_name="worker"} | trace_id="<id>"`.

## Where the values come from

`OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` are set in
each of `services/{users,budget,ai,chat,worker}/.env.*.prod` as
`${GRAFANA_CLOUD_OTLP_ENDPOINT}` / `${GRAFANA_CLOUD_OTLP_HEADERS}`
placeholders — never a real value in the committed template.
`.github/workflows/deploy.yml`'s env-file regeneration step substitutes the
real values from the `GRAFANA_CLOUD_OTLP_ENDPOINT` and
`GRAFANA_CLOUD_OTLP_HEADERS` GitHub Actions secrets in place on the server at
deploy time, the same way `JWT_SECRET_KEY` and the other prod secrets already
work — no new secret was needed for the worker or for logs, since both reuse
the same two.

Provisioning the Grafana Cloud org/stack, generating the scoped API token,
and setting those two secrets is a one-time manual step done outside this
repo (Grafana Cloud console + `gh secret set` / repo Settings → Secrets).

## Viewing traces, metrics, and logs

Log into the Grafana Cloud stack and use:

- **Explore → Tempo** (or the trace search view) — filter by `service.name`
  (`users-service`, `budget-service`, `ai-service`, `chat-service`, `worker`
  — the argument each service passes to `init_observability`) to find traces
  for a given service.
- **Explore → Prometheus/Mimir** — query the auto-instrumented FastAPI/SQLAlchemy
  metrics (request rate, duration histograms, DB query spans) and the
  worker's own `worker_tasks_total` counter.
- **Explore → Loki** — see [Searching logs in Grafana](#searching-logs-in-grafana)
  above.
- **Dashboards** — the starter dashboard is checked into
  [`monitoring/grafana-cloud/dashboard.json`](../../monitoring/grafana-cloud/dashboard.json)
  and importable via Grafana Cloud's dashboard JSON import. Its "Activity
  rate" and "Error rate" panels combine all five services into one line per
  service each — HTTP request/5xx rate for `users`/`budget`/`ai`/`chat`,
  task/task-failure rate for `worker` — plus p95/p99 HTTP latency (FastAPI
  services only, worker has no request latency to measure) and two
  worker-only drill-down panels broken out by task name.

## Free-tier limits

The free tier caps at 10k active metric series, 50GB traces/month, and a
log-ingestion volume cap (see the Grafana Cloud usage page for the exact
current number) — all with 14-day retention. FastAPI/SQLAlchemy
auto-instrumentation labels by route template and statement type, not raw
values, so metric series count should stay well under the cap at this app's
traffic.

Log volume is the newer risk: root logger level defaults to `INFO` across
all five services, which also captures framework-level noise (e.g. every
Celery task-lifecycle log line, not just failures). <!-- TODO: after a few
days of production traffic, check actual log ingestion volume against the
free-tier quota here and drop the level to WARNING if it's a problem. -->

## Out of scope

Alerting rules on error rate or log content are not configured — noted as a
future follow-on, not covered by this setup.
