## ADDED Requirements

### Requirement: Production services ship structured logs to Grafana Cloud Loki
Each production service (`users`, `budget`, `ai`, `chat`, `worker`) SHALL export application logs — including framework-level logs such as Celery's own task-failure traceback logging — via OTLP to Grafana Cloud Loki, using the same OTLP endpoint and credentials already configured for traces and metrics.

#### Scenario: A service logs an error
- **WHEN** any production service emits a log record via the standard `logging` module at `INFO` level or above
- **THEN** the log record is exported via OTLP to Grafana Cloud, tagged with `service.name`, and visible in Grafana's log search within a few minutes, without requiring SSH access to the production host

#### Scenario: An unhandled exception is logged by a framework component
- **WHEN** Celery's internal machinery logs a task failure traceback (as it already does today, visible only via `docker logs`)
- **THEN** that same traceback is also exported as an OTLP log record and visible in Grafana's log search, since the OTLP logging handler is attached at the root logger

### Requirement: Logs are correlated to traces when a span is active
Log records emitted while a trace span is active SHALL include that span's trace ID and span ID, so a log line can be traced back to the request or task that produced it.

#### Scenario: A log is emitted during a traced task execution
- **WHEN** a log record is emitted inside a Celery task that is currently wrapped in an active span (per `worker-observability`)
- **THEN** the exported log record includes the active span's `trace_id` and `span_id`, allowing the log to be found from the corresponding trace in Grafana Cloud

### Requirement: Log export respects the existing telemetry disable flag
Setting `OTEL_SDK_DISABLED=true` for a service SHALL fully disable log export for that service, identically to how it disables trace and metric export.

#### Scenario: Operator disables telemetry for a service
- **WHEN** `OTEL_SDK_DISABLED=true` is set for a production service and it is restarted
- **THEN** no OTLP log export calls are made by that service, and its logs remain local-only (`docker logs`) exactly as they were before this change

### Requirement: Log export uses batched, non-blocking delivery
Log export SHALL NOT block the request/task path on network I/O to the OTLP gateway.

#### Scenario: The OTLP gateway is slow or briefly unreachable
- **WHEN** a service emits log records while Grafana Cloud's OTLP gateway is slow to respond or briefly unreachable
- **THEN** the service's request/task handling continues without added latency, and buffered log records are exported in the background once the gateway is reachable (or dropped after the batch processor's retry/backoff limit, without crashing the service)
