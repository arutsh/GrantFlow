One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Worker traces + metrics instrumentation

- [ ] 1.1 Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` (pinned to the same `1.43.0` used by `users`/`budget`/`ai`/`chat`) to `services/worker/requirements.txt`.
- [ ] 1.2 Call `init_observability("worker")` once at import time in `services/worker/celery_app.py`.
- [ ] 1.3 Add Celery `task_prerun`/`task_postrun`/`task_failure` signal handlers in `celery_app.py`: start a span named after the task on `task_prerun`, end it on `task_postrun`, and on `task_failure` set span status `ERROR` + `record_exception()`; increment a `worker.tasks` counter metric with `{task_name, status}` attributes in both the success and failure paths.
- [ ] 1.4 Add `OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_EXPORTER_OTLP_HEADERS`/`OTEL_SDK_DISABLED` placeholder vars to `services/worker/.env.worker.prod` (and `.env.worker.dev`/`.env.worker.local` pointed at the local OTel Collector, matching the other services' dev defaults).
- [ ] 1.5 Update `.github/workflows/deploy.yml`'s env-file regeneration step so `services/worker/.env.worker.prod`'s new OTLP vars are populated from the existing `GRAFANA_CLOUD_OTLP_ENDPOINT`/`GRAFANA_CLOUD_OTLP_HEADERS` secrets (no new secret needed).
- [ ] 1.6 Add tests covering: `OTEL_SDK_DISABLED` no-ops the worker's signal handlers, a successful task increments the success counter, a failing task increments the failure counter and records the exception on the span.
- [ ] 1.7 Run `services/worker` tests/lint (`flake8 --max-line-length=100`) clean; PR merged (`Closes` the ticket for this group).

## 2. Shared OTLP logs export module — depends on 1

- [ ] 2.1 Extend `shared/observability/__init__.py` with `init_logging(service_name)`: build a `LoggerProvider` + `BatchLogRecordProcessor` + `OTLPLogExporter` pointed at `<base_endpoint>/v1/logs` (same endpoint/header resolution logic already used for traces/metrics), attach a `LoggingHandler` to the root `logging` logger, and bail out as a no-op when `OTEL_SDK_DISABLED` is set — mirror `init_observability`'s existing env-normalization and endpoint-suffix logic exactly rather than duplicating it ad hoc.
- [ ] 2.2 Confirm (via a manual/local test) that log records emitted while a span is active are automatically tagged with that span's `trace_id`/`span_id` by the SDK's default log-trace correlation.
- [ ] 2.3 Add test coverage to `shared/tests/`: disabled bail-out, local-dev default endpoint, Grafana Cloud endpoint forwarding (`/v1/logs` suffix), a log emitted inside an active span carries trace/span IDs.
- [ ] 2.4 Run `shared` tests/lint clean; PR merged (`Closes` the ticket for this group).

## 3. Wire logs into all five services — depends on 1, 2

- [ ] 3.1 Call `init_logging(service_name)` alongside the existing `init_observability(service_name)` call in each of `services/users/main.py`, `services/budget/main.py`, `services/ai/main.py`, `services/chat/main.py`, and `services/worker/celery_app.py`.
- [ ] 3.2 Set each service's root logger level to `INFO` where not already configured, so both explicit `logger.*()` calls and framework-level logging (e.g. Celery's own task-failure traceback) are captured.
- [ ] 3.3 Verify locally against the dev OTel Collector that a deliberately raised exception in a worker task produces both a spans-tab entry (from group 1) and a matching log entry with the same trace ID.
- [ ] 3.4 Run tests/lint clean across all five affected services; PR merged (`Closes` the ticket for this group).

## 4. Production rollout, dashboard, and docs — depends on 1, 2, 3

- [ ] 4.1 Deploy to production (push to `main` or manual `workflow_dispatch`).
- [ ] 4.2 Trigger one task per worker task type and one request per FastAPI service; confirm matching spans, metrics, and logs all appear in Grafana Cloud for all five services.
- [ ] 4.3 Deliberately reproduce a worker task failure (or wait for a real one) and confirm it's discoverable from the Grafana Cloud dashboard/log search alone, without SSH — the scenario that originally motivated this change.
- [ ] 4.4 Add `worker` task-rate and failure-rate panels to `monitoring/grafana-cloud/dashboard.json`, alongside the existing per-service panels.
- [ ] 4.5 Add a log-search/Explore link or panel to the dashboard (or document the query in the doc from 4.6) for filtering logs by `service.name`.
- [ ] 4.6 Update `docs/observability/GRAFANA_CLOUD_PRODUCTION.md` to document worker instrumentation, the logs pipeline, and how to search logs/correlate to traces in Grafana.
- [ ] 4.7 Check actual log ingestion volume against the Grafana Cloud free-tier log quota after a few days of production traffic; note the result in the doc from 4.6 and adjust root logger level if quota pressure is a concern.
- [ ] 4.8 PR merged (`Closes` the ticket for this group).
