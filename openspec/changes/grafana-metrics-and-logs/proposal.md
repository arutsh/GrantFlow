## Why

A prod Mailjet config error (`services/worker/tasks/users/send_verification_email.py` crashing on `int("")`) was invisible in Grafana Cloud's golden-signals dashboard and only found by SSHing in and reading `docker logs` directly. Two gaps caused this: `services/worker` (the Celery worker) never calls `init_observability()` — unlike `users`/`budget`/`ai`/`chat` — so it emits no traces or metrics at all; and no service ships application logs to Grafana Cloud (Loki), so even instrumented services only give a "something failed" signal, never the traceback. `production-observability` (the prior Grafana Cloud rollout) explicitly scoped both out as follow-ons.

## What Changes

- Instrument `services/worker` with the same `shared/observability` module the FastAPI services use: call `init_observability("worker")` in `celery_app.py`, and hook Celery's `task_prerun`/`task_success`/`task_failure` signals to create a span per task execution, mark it errored with the exception on failure, and export a task-count metric — bringing worker onto the same request-rate/error-rate dashboard pattern.
- Add a Loki logging pipeline for all five services (`users`, `budget`, `ai`, `chat`, `worker`): ship structured stdout logs to Grafana Cloud Loki via OTLP logs (reusing the same `OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_EXPORTER_OTLP_HEADERS` credentials already wired for traces/metrics) or via a lightweight log-shipping sidecar/driver, whichever `design.md` lands on.
- Extend `shared/observability/__init__.py` with a logs-export path (`LoggerProvider`/`OTLPLogExporter`) alongside the existing trace/metric providers, gated by the same `OTEL_SDK_DISABLED` bail-out.
- Add worker + error-rate panels to the existing `monitoring/grafana-cloud/dashboard.json`, and a log-search/explore view or link.
- Update `docs/observability/GRAFANA_CLOUD_PRODUCTION.md` to document the worker instrumentation and log pipeline.

## Capabilities

### New Capabilities
- `worker-observability`: the Celery worker service exports traces and metrics via OTLP to Grafana Cloud for each task execution, including failure status and exception detail, visible on the production dashboard.
- `production-log-shipping`: all production services ship structured application logs to Grafana Cloud Loki, queryable without SSH access to the production host.

### Modified Capabilities
- `production-observability`: extends the existing per-service OTLP export (currently traces+metrics for `users`/`budget`/`ai`/`chat` only) to also cover the `worker` service; not yet archived to `openspec/specs/`, so this change absorbs and supersedes its still-open follow-on items rather than editing an established spec.

## Impact

- **Code**: `services/worker/celery_app.py` (signal handlers), `services/worker/requirements.txt` (OTEL deps, currently absent), `shared/observability/__init__.py` (logs export + Celery instrumentation helper), each service's log configuration (`main.py` / logging setup) to route through the new OTLP logs path.
- **Config/secrets**: reuse existing `OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_EXPORTER_OTLP_HEADERS` where possible; `services/worker/.env.worker.prod` gains the same OTLP placeholders the four FastAPI services already have.
- **Infra**: no new containers required if using OTLP logs directly to Grafana Cloud; a local log-shipping sidecar is out unless `design.md` finds OTLP-logs-from-stdout impractical.
- **Docs**: `docs/observability/GRAFANA_CLOUD_PRODUCTION.md`, `monitoring/grafana-cloud/dashboard.json`.
- **Dependencies**: likely adds `opentelemetry-exporter-otlp-proto-http` (logs) and Celery OTEL instrumentation to `services/worker/requirements.txt`.
