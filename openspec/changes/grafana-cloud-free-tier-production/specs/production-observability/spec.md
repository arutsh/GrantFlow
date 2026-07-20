## ADDED Requirements

### Requirement: Production services export telemetry to Grafana Cloud
Each production FastAPI service (`users`, `budget`, `ai`, `chat`) SHALL export OpenTelemetry traces and metrics via OTLP over TLS to the configured Grafana Cloud endpoint, using credentials supplied via environment variables, without requiring any additional monitoring container in `docker-compose.prod.yml`.

#### Scenario: Service starts with Grafana Cloud credentials configured
- **WHEN** a production service starts with `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` set to Grafana Cloud's OTLP gateway endpoint and Basic Auth header
- **THEN** the service initializes an OTLP exporter that connects over TLS and authenticates with the configured header, and begins exporting traces and metrics for incoming requests

#### Scenario: A production request produces a visible trace
- **WHEN** a real HTTP request is handled by any of the four production services
- **THEN** a corresponding trace for that request is visible in Grafana Cloud's trace search within a few minutes, tagged with the correct `service.name`

### Requirement: Local development observability is unaffected
Local development SHALL continue to export traces and metrics insecurely to the local OTel Collector without requiring any Grafana Cloud credentials, and without any developer-facing configuration change.

#### Scenario: Developer runs services locally with no Grafana Cloud env vars set
- **WHEN** a service starts locally with `OTEL_EXPORTER_OTLP_ENDPOINT` unset or pointed at `localhost:4317`, and no `OTEL_EXPORTER_OTLP_HEADERS` set
- **THEN** the service exports traces and metrics insecurely to the local OTel Collector exactly as it did before this change

### Requirement: Telemetry export can be fully disabled via a single flag
Operators SHALL be able to disable all telemetry export for a service by setting `OTEL_SDK_DISABLED=true`, without any code change or redeploy of application code.

#### Scenario: Operator disables telemetry in production
- **WHEN** `OTEL_SDK_DISABLED=true` is set for a production service and the service is restarted
- **THEN** `init_observability()` returns immediately as a no-op and the service makes no OTLP export calls

### Requirement: Secrets never appear in committed template files
The Grafana Cloud OTLP endpoint and authentication header/token SHALL be supplied only via secrets injected at deploy time, and committed `.env.prod` / `services/*/.env.*.prod` template files SHALL contain only placeholder references, never a real endpoint or token value.

#### Scenario: Repository is inspected for leaked credentials
- **WHEN** the committed `.env.prod` and `services/*/.env.*.prod` files are inspected
- **THEN** any Grafana Cloud-related variable appears only as a `${VAR}` placeholder, with the real value populated only on the server at deploy time from GitHub Actions secrets

### Requirement: Starter dashboard covers core golden signals per service
The Grafana Cloud stack SHALL include a dashboard showing, per production service, request rate, error rate, and p95/p99 request latency, sourced from the exported OTLP metrics.

#### Scenario: Engineer opens the starter dashboard after rollout
- **WHEN** an engineer opens the provisioned Grafana Cloud dashboard after at least one production service has been sending metrics for a few minutes
- **THEN** the dashboard renders non-empty request rate, error rate, and latency percentile panels for each active service
