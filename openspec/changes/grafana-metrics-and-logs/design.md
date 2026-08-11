## Context

`shared/observability/__init__.py` wires OTLP traces + metrics from `users`/`budget`/`ai`/`chat` to Grafana Cloud's OTLP/HTTP gateway (`https://otlp-gateway-<region>.grafana.net/otlp`), authenticated via `OTEL_EXPORTER_OTLP_HEADERS` (Basic Auth). `services/worker` (Celery, `celery_app.py`) never calls `init_observability()` and has zero OpenTelemetry packages in `requirements.txt` — it is completely invisible to Grafana Cloud. Neither the worker nor the four FastAPI services ship application logs anywhere; a production incident (Mailjet template-ID crash) was only found by SSHing in and reading `docker logs` on the container directly. The worker's own task code doesn't call `logging` at all — the traceback that was visible in `docker logs` came from Celery's own internal task-failure logging, not app-level log statements.

Grafana Cloud's OTLP gateway (the same endpoint already in use) accepts logs at `/v1/logs` alongside `/v1/traces` and `/v1/metrics` — Grafana Cloud Loki has supported native OTLP log ingestion since 2023, so no new endpoint, credential, or gateway config is needed, only a third exporter pointed at the same base URL.

opentelemetry-exporter-otlp-proto-http==1.43.0 (already pinned in the four FastAPI services) ships `opentelemetry.sdk._logs.LoggerProvider`/`LoggingHandler` and `opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter` — verified importable in the current environment. No version bump needed; the worker just needs the same packages the other services already carry.

## Goals / Non-Goals

**Goals:**
- Worker task executions become visible in Grafana Cloud as spans (with error status + exception recorded on failure) and a task-count metric, following the exact pattern `init_observability()` already establishes for the FastAPI services.
- All five services (`users`, `budget`, `ai`, `chat`, `worker`) ship structured logs to Grafana Cloud Loki via OTLP, queryable in Grafana without SSH/`docker logs` access, and correlated to the active trace/span when one exists.
- No new infrastructure container in `docker-compose.prod.yml`; export happens directly from each process, same as traces/metrics.

**Non-Goals:**
- Alerting rules on error rate or log content (separate future change, same as the prior observability rollout deferred this).
- Auto-instrumenting Celery via a third-party package (`opentelemetry-instrumentation-celery` isn't reliably available/maintained against current OTEL SDK versions) — hand-rolled signal handlers instead, consistent with how `shared/observability` already hand-calls `FastAPIInstrumentor`/`SQLAlchemyInstrumentor` rather than blanket auto-instrumenting.
- Retroactively adding rich `logger.info`/`logger.error` calls throughout existing business logic — this change wires the *pipeline*; call sites get filled in opportunistically on touch, not swept in one pass.
- Log-based dashboards/panels beyond a basic Explore/log-search link — full log dashboards are a follow-on.

## Decisions

**1. Celery instrumentation: manual signal handlers, not an auto-instrumentation package.**
Hook `task_prerun`, `task_postrun`, and `task_failure` Celery signals in `celery_app.py` to start/end a span per task (`get_tracer("worker").start_as_current_span(task.name)`), set span status `ERROR` and `record_exception()` on `task_failure`, and increment a `worker.tasks` counter metric with `{task_name, status}` attributes. Alternative considered: `opentelemetry-instrumentation-celery` — rejected because it wasn't resolvable in this environment and would add a dependency whose OTEL SDK version compatibility isn't verified against the `1.43.0`/`0.64b0` pins already standardized across the repo; manual signals are ~30 lines and match the existing hand-rolled style.

**2. Logs: `opentelemetry.sdk._logs` + stdlib `logging.Handler`, not a sidecar log shipper.**
Add a `init_logging(service_name)` (or extend `init_observability`) that attaches an OTLP `LoggingHandler` to the root `logging` logger. This captures both explicit `logger.*()` calls and, critically, Celery's own internal task-failure logging (the exact traceback that was only in `docker logs` before) without any code change inside Celery itself, since Celery logs through the stdlib `logging` module. Alternative considered: Promtail/Grafana Agent sidecar scraping `docker logs` — rejected as it adds a new container per the prior change's stated goal of "near-zero added container footprint," and would ship raw unstructured text instead of OTLP log records correlated to trace/span IDs.

**3. Same OTLP gateway/credentials, new `/v1/logs` path — no new secrets.**
Reuse `OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_EXPORTER_OTLP_HEADERS` already present for the four FastAPI services; `init_observability`/`init_logging` appends `/v1/logs` the same way it already appends `/v1/traces` and `/v1/metrics`. `services/worker/.env.worker.prod` gains the same two placeholder vars the other four services already have, wired through the existing `deploy.yml` secret-substitution step (no new GitHub Actions secret).

**4. Worker gets `init_observability("worker")` called once at Celery app import time**, not per-task, mirroring how each FastAPI service calls it once at startup in `main.py`.

## Risks / Trade-offs

- [Adding a logging handler that exports synchronously per log record could add latency/backpressure to hot paths] → Mitigation: use `BatchLogRecordProcessor` (batches + background export thread), same pattern already used for `BatchSpanProcessor`.
- [Log volume could consume the Grafana Cloud free-tier log ingestion quota faster than traces/metrics did] → Mitigation: default root logger level stays at `INFO`; verify quota headroom during rollout (task list includes a quota check, mirroring how the prior change checked metric series count).
- [Celery signal handlers run in the worker process for every task, including high-frequency ones like `cleanup_sessions`] → Mitigation: this worker only runs three lightly-used task types today (`tasks.ai.cleanup_sessions`, `tasks.debug.ping`, `tasks.users.send_verification_email`), so per-task span/metric overhead is negligible; revisit if task volume grows significantly.
- [`OTEL_SDK_DISABLED` must still fully no-op the new logs path] → Mitigation: `init_logging` checks the same env var and bails out identically to `init_observability`, verified by extending the existing test coverage.

## Migration Plan

1. Extend `shared/observability/__init__.py` with logs export + tests (no behavior change for existing callers).
2. Add worker instrumentation (`celery_app.py` signals) and `services/worker/requirements.txt` OTEL deps; verify locally against dev's OTel Collector before touching prod.
3. Add OTLP env placeholders to `services/worker/.env.worker.prod` and `deploy.yml`'s secret-substitution step.
4. Deploy; send a test task and a test request to each of the five services; confirm spans/metrics/logs all land in Grafana Cloud.
5. Rollback: identical to the existing mechanism — set `OTEL_SDK_DISABLED=true` per service and redeploy; no data migration involved.

## Open Questions

- Should log level default to `INFO` or `WARNING` in production, given free-tier log-ingestion volume is unverified? (Task list includes checking actual usage post-rollout before deciding.)
- Does `production-observability`'s still-open change (`grafana-cloud-free-tier-production`) get archived before or after this change lands? This change's tasks.md should note it supersedes that change's unchecked worker/logs follow-on items regardless of archive order.
