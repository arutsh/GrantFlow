## Why

Production runs on a 4GB Hetzner box with zero observability: all four FastAPI services (`users`, `budget`, `ai`, `chat`) already call `init_observability()` from `shared/observability/__init__.py` at startup, which defaults to exporting OTLP traces/metrics to `localhost:4317` — a port nothing is listening on in prod, so every export silently fails in the background. The full Jaeger + Prometheus + Grafana + OTel Collector stack that exists in `docker-compose.dev.yml` was already flagged as too heavy to run alongside the app containers on a 4GB box. Grafana Cloud's free tier (10k metric series, 50GB traces, 14-day retention) gives us a hosted collector/backend that the existing OTLP exporters can point at directly, at zero added infra cost and near-zero added container footprint on the server.

## What Changes

- Provision a Grafana Cloud free-tier stack (Grafana Cloud account/org, if one doesn't already exist) and capture its OTLP gateway endpoint + access policy token.
- Extend `shared/observability/__init__.py` so `init_observability()` can talk TLS + Basic Auth to a remote OTLP endpoint, instead of always forcing `insecure=True` — driven by env vars so local dev behavior (insecure, local collector) is unchanged.
- Add the new env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, and an insecure/secure toggle) to `.env.prod` template and each service's `.env.*.prod` template, and wire real values through the existing GitHub Actions secrets → deploy workflow path.
- No new containers added to `docker-compose.prod.yml` — traces and metrics are exported straight from each service process to Grafana Cloud, no local collector/Jaeger/Prometheus/Grafana needed in prod.
- Import (or hand-build) a starter Grafana Cloud dashboard covering request rate, error rate, and p95/p99 latency per service, plus a basic trace-search view.
- Document the setup in `docs/observability/` (new prod-specific doc) and update `docs/deployment/DEPLOYMENT_MODES.md`'s production section to mention where telemetry goes.

Out of scope for this change: shipping application logs to Grafana Cloud Loki (kept as a follow-on; current prod logs stay as `docker logs`), and alerting rules (noted as future work).

## Capabilities

### New Capabilities
- `production-observability`: production services export traces and metrics via OTLP to a hosted Grafana Cloud free-tier stack, with dashboards for the core golden-signal metrics (rate, errors, duration) per service, without adding any monitoring containers to the production compose stack.

### Modified Capabilities
(none — no existing spec-level capability covers this repo yet)

## Impact

- **Code**: `shared/observability/__init__.py` (exporter construction logic — auth headers, TLS), no changes needed in the four `main.py` call sites since they already call `init_observability(service_name)` with no explicit endpoint.
- **Config/secrets**: `.env.prod`, `services/*/.env.*.prod` templates gain new placeholder vars; real values added as GitHub Actions secrets and consumed by `.github/workflows/deploy.yml`'s existing "regenerate env files" step.
- **Infra**: none added to `docker-compose.prod.yml` or `terraform/` — this is purely an external SaaS integration plus service-level config.
- **Docs**: new prod observability doc under `docs/observability/`; `DEPLOYMENT_MODES.md` production section updated.
- **Dependencies**: existing `opentelemetry-exporter-otlp-proto-grpc` (or HTTP variant, TBD in design) already in requirements — may need a version bump to support TLS/header auth cleanly; no other new packages.
