## Context

Production (`docker-compose.prod.yml`, one 4GB Hetzner box) runs four FastAPI services (`users`, `budget`, `ai`, `chat`), a Celery worker + beat, Postgres, Redis, RabbitMQ, and Caddy. Every service already calls `shared/observability/init_observability(service_name)` at startup, which unconditionally builds:

```python
OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
```

with `otlp_endpoint` defaulting to `OTEL_EXPORTER_OTLP_ENDPOINT` env var or `localhost:4317`. In prod, that env var is unset and nothing listens on `localhost:4317`, so every service silently retries a doomed export forever. Dev has a full local stack (Jaeger + Prometheus + Grafana + OTel Collector, `docker-compose.dev.yml`) that was already judged too heavy to replicate on the 4GB prod box (see prior observability-backlog notes). Grafana Cloud's free tier (10k active metric series, 50GB traces/mo, 14-day retention, one user seat beyond the 3 included) gives a hosted backend that the existing OTLP exporters can talk to directly — no new prod containers.

## Goals / Non-Goals

**Goals:**
- Real traces and metrics from all four prod services visible in a hosted Grafana Cloud instance, with zero new containers on the prod box.
- Reuse the existing `init_observability()` call sites unchanged — only the shared module's exporter construction changes.
- Keep local dev behavior (insecure, local OTel Collector) working exactly as today with no env changes required for dev.
- A basic starter dashboard (per-service request rate, error rate, p95/p99 latency) and working trace search, so the SaaS switch is immediately useful, not just plumbing.
- Stay comfortably inside the free-tier metric-series budget (10k active series) — this mainly means not adding high-cardinality labels to auto-instrumented metrics.

**Non-Goals:**
- Shipping logs to Grafana Cloud Loki. Current `docker logs`-based flow stays as-is; log shipping is a separate follow-on change.
- Alerting rules / on-call integration. Noted as future work once there's a reason to page someone.
- A local OTel Collector / gateway in prod. Direct service → Grafana Cloud OTLP export is sufficient at this scale and keeps the box lighter.
- Changing what's instrumented (FastAPI + SQLAlchemy auto-instrumentation stays as-is); this change is about where telemetry goes, not what's collected.

## Decisions

**1. Direct-to-cloud OTLP export, no local collector in prod.**
The existing dev stack routes through `otel-collector` → Jaeger/Prometheus. Replicating that in prod would mean 3-4 more containers on a 4GB box for a low-traffic, cost-constrained deployment. Grafana Cloud exposes an OTLP gateway endpoint that accepts gRPC or HTTP OTLP directly with Basic Auth, so each service's existing `BatchSpanProcessor`/`PeriodicExportingMetricReader` can export straight to it. Trade-off: no local buffering across a Grafana Cloud outage beyond what the OTel SDK batches in-process — acceptable for a low-traffic prod app; a dropped batch during a rare SaaS outage is not worth a local durable queue at this scale.

**2. Extend `shared/observability/__init__.py` instead of forking per-service config.**
All four services already share this one module and call it identically (`init_observability(service_name)` with no explicit endpoint). The fix is entirely inside `init_observability`:
- Derive `insecure` from the endpoint's scheme/env flag instead of hardcoding `True`. Local dev keeps `insecure=True` (plain `localhost:4317`); prod sets an env flag so the exporters negotiate TLS.
- Read `OTEL_EXPORTER_OTLP_HEADERS` (standard OTel env var, e.g. `authorization=Basic <base64(instance_id:api_token)>`) and pass it into both exporters' `headers=` kwarg.
- Everything else (`Resource`, `TracerProvider`, `SQLAlchemyInstrumentor`, `OTEL_SDK_DISABLED` bail-out) is unchanged.
This keeps the four `main.py` call sites at zero diff — the whole change is config-driven.

**3. Keep the existing gRPC OTLP exporters (`opentelemetry-exporter-otlp-proto-grpc`) rather than switching to the HTTP variant.**
Grafana Cloud's OTLP gateway accepts both gRPC and HTTP/protobuf. Switching exporter packages would touch every service's `requirements.txt` and both exporter classes for no functional gain, since gRPC-over-TLS-443 works fine outbound from a Docker host. Revisit only if a real connectivity problem shows up against Grafana Cloud's actual gateway (open question below).

**4. Secrets flow through the existing GitHub Actions → deploy.yml path, not a new mechanism.**
`deploy.yml` already regenerates `.env.prod` and `services/*/.env.*.prod` on the server from GitHub Actions secrets at deploy time. Add `GRAFANA_CLOUD_OTLP_ENDPOINT` and `GRAFANA_CLOUD_OTLP_HEADERS` (or split instance-id/token so the header value is assembled on the runner, whichever keeps the raw API token out of a single easily-copy-pasted secret — decide during implementation) as new secrets, consumed the same way `JWT_SECRET_KEY` etc. already are. No new secret-delivery mechanism.

**5. Rollback is a single env flag, not a code revert.**
`OTEL_SDK_DISABLED=true` already short-circuits `init_observability()` to a no-op. If the Grafana Cloud integration misbehaves (e.g. unexpectedly high series cardinality, connectivity issues), ops can set that flag in `.env.prod` and redeploy — no code change needed to fully disable telemetry export.

## Risks / Trade-offs

- **[Metric cardinality exceeds free-tier 10k series]** → FastAPI/SQLAlchemy auto-instrumentation labels by route template and DB statement type, not raw values, so this is unlikely at current traffic; monitor active series count in Grafana Cloud's usage page after rollout and prune/relabel if it climbs.
- **[Outbound TLS/gRPC to Grafana Cloud blocked or flaky from Hetzner]** → Caddy already proves outbound 443 works from the box; if gRPC specifically has issues, fall back to the OTLP/HTTP exporter variant (same endpoint family, different port/path) as a follow-up, not a blocker for this change.
- **[API token leakage]** → the Basic Auth header embeds a long-lived Grafana Cloud API token; treat it exactly like the other prod secrets already in GitHub Actions (never committed, regenerated in place on deploy) — no template `.env.prod` file should ever contain a real token, only `${VAR}` placeholders, consistent with existing convention.
- **[Free tier exhausted or Grafana Cloud pricing changes]** → 14-day retention and 10k series / 50GB traces is generous for this app's current scale; if usage grows, this is a config change to a paid tier, not an architecture change, since the export path doesn't change.
- **[No local fallback during a Grafana Cloud outage]** → accepted; traces/metrics for that window are lost, but nothing in the app depends on telemetry being delivered (fire-and-forget), so this cannot cause a prod incident by itself.

## Migration Plan

1. Create (or reuse) a Grafana Cloud org + free-tier stack; note the OTLP gateway endpoint and generate a scoped API token (traces + metrics write).
2. Add `GRAFANA_CLOUD_OTLP_ENDPOINT` / `GRAFANA_CLOUD_OTLP_HEADERS` (or equivalent split secrets) to the GitHub repo's Actions secrets.
3. Update `shared/observability/__init__.py` to support TLS + header auth via env vars, defaulting to today's insecure local behavior when those env vars are absent.
4. Add the new placeholder vars to `.env.prod` and each `services/*/.env.*.prod` template, and reference them in `deploy.yml`'s env-file regeneration step.
5. Deploy via the normal `main` push flow (or manual `workflow_dispatch`); confirm traces/metrics land in Grafana Cloud (Explore view) for at least one real request per service.
6. Import/build the starter dashboard (request rate, error rate, p95/p99 latency per service) in the Grafana Cloud stack.
7. Update `docs/observability/` and `docs/deployment/DEPLOYMENT_MODES.md` production section.

Rollback: set `OTEL_SDK_DISABLED=true` in `.env.prod`, redeploy (or `workflow_dispatch`) — reverts to today's no-op state with no code change.

## Open Questions

- Split the Basic Auth token into `GRAFANA_CLOUD_INSTANCE_ID` + `GRAFANA_CLOUD_API_TOKEN` secrets and assemble the header at deploy time, vs. storing one pre-encoded `GRAFANA_CLOUD_OTLP_HEADERS` secret directly — decide during implementation based on what's easiest to rotate.
- Confirm the exact OTLP gateway hostname/port for the chosen Grafana Cloud region once the stack is provisioned (varies per stack, e.g. `otlp-gateway-<region>.grafana.net:443`).
- Whether to also forward Celery worker/beat telemetry in this change or leave them uninstrumented for now — proposal scopes this to the four FastAPI services only; worker instrumentation can be a fast follow if desired.
