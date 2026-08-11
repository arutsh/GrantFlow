## ADDED Requirements

### Requirement: Worker exports task execution telemetry to Grafana Cloud
The `worker` service SHALL export a trace span and a task-count metric for every Celery task execution via OTLP to the configured Grafana Cloud endpoint, using the same `init_observability()` mechanism and environment variables as the FastAPI services.

#### Scenario: A task runs to completion
- **WHEN** any Celery task registered in `celery_app.py` (e.g. `tasks.users.send_verification_email`) executes and returns successfully
- **THEN** a span is exported tagged with `service.name=worker` and the task name, with a status of OK, and the `worker.tasks` counter metric is incremented with a `status=success` attribute

#### Scenario: A task raises an unhandled exception
- **WHEN** a Celery task raises an exception that is not caught and results in `task_failure`
- **THEN** the corresponding span is marked with error status and the exception is recorded on the span, and the `worker.tasks` counter metric is incremented with a `status=failure` attribute, without requiring anyone to inspect `docker logs` to discover the failure occurred

### Requirement: Worker respects the existing telemetry disable flag
Setting `OTEL_SDK_DISABLED=true` for the worker service SHALL fully disable worker telemetry export, identically to how it disables telemetry for the FastAPI services.

#### Scenario: Operator disables telemetry for the worker
- **WHEN** `OTEL_SDK_DISABLED=true` is set for the worker service and it is restarted
- **THEN** `init_observability("worker")` returns immediately as a no-op, no Celery signal handlers attempt to export spans or metrics, and no OTLP export calls are made

### Requirement: Worker telemetry appears on the production dashboard
The Grafana Cloud dashboard used for production golden signals SHALL include a `worker` panel showing task execution rate and failure rate, alongside the existing per-service panels.

#### Scenario: Engineer opens the dashboard after worker instrumentation is deployed
- **WHEN** an engineer opens the production Grafana Cloud dashboard after the worker has processed at least one task since deployment
- **THEN** a worker task-rate panel and a worker failure-rate panel render non-empty data, distinguishable from the `users`/`budget`/`ai`/`chat` service panels
