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
The existing dev stack routes through `otel-collector` → Jaeger/Prometheus. Replicating that in prod would mean 3-4 more containers on a 4GB box for a low-traffic, cost-constrained deployment. Grafana Cloud exposes an OTLP gateway endpoint that accepts HTTP/protobuf OTLP directly with Basic Auth, so each service's existing `BatchSpanProcessor`/`PeriodicExportingMetricReader` can export straight to it. Trade-off: no local buffering across a Grafana Cloud outage beyond what the OTel SDK batches in-process — acceptable for a low-traffic prod app; a dropped batch during a rare SaaS outage is not worth a local durable queue at this scale.

**2. Extend `shared/observability/__init__.py` instead of forking per-service config.**
All four services already share this one module and call it identically (`init_observability(service_name)` with no explicit endpoint). The fix is entirely inside `init_observability`:
- TLS is derived automatically from the endpoint's `http`/`https` scheme by the exporter itself — no custom logic needed.
- `OTEL_EXPORTER_OTLP_HEADERS` (standard OTel env var, e.g. `authorization=Basic <base64(instance_id:api_token)>`) is read directly by each exporter from the environment when `headers=` isn't passed explicitly — also no custom logic needed.
- `init_observability` appends `/v1/traces` / `/v1/metrics` to the resolved base endpoint by hand, since passing an explicit `endpoint=` (as we do, to support the deprecated `otlp_endpoint` override param) bypasses the exporters' own auto-append-on-env-fallback behavior.
- Everything else (`Resource`, `TracerProvider`, `SQLAlchemyInstrumentor`, `OTEL_SDK_DISABLED` bail-out) is unchanged.
This keeps the four `main.py` call sites at zero diff — the whole change is config-driven.

**3. Use the OTLP/HTTP exporters (`opentelemetry-exporter-otlp-proto-http`), not gRPC.**
Originally planned to keep the existing gRPC exporters, reasoning gRPC-over-TLS-443 would work fine outbound and switching packages would touch every service's `requirements.txt` for no functional gain. **Superseded during implementation**: tested directly against the production OTLP gateway and confirmed with Grafana support that **Grafana Cloud's OTLP gateway does not accept gRPC at all, in any region** — its fronting proxy is HTTP/1.1-only and never negotiates ALPN for `h2`, so `grpc-core` refuses the TLS handshake before any request is even sent (verified independently of any client library via raw `openssl s_client -alpn h2`, which showed "No ALPN negotiated"). OTLP/HTTP is the only transport the gateway supports. No `requirements.txt` change was actually needed — `opentelemetry-exporter-otlp-proto-http` was already present in every service's requirements (bundled via the umbrella `opentelemetry-exporter-otlp` package) alongside the now-unused gRPC variant.

**4. Secrets flow through the existing GitHub Actions → deploy.yml path, not a new mechanism.**
`deploy.yml` already regenerates `.env.prod` and `services/*/.env.*.prod` on the server from GitHub Actions secrets at deploy time. Add `GRAFANA_CLOUD_OTLP_ENDPOINT` and `GRAFANA_CLOUD_OTLP_HEADERS` (or split instance-id/token so the header value is assembled on the runner, whichever keeps the raw API token out of a single easily-copy-pasted secret — decide during implementation) as new secrets, consumed the same way `JWT_SECRET_KEY` etc. already are. No new secret-delivery mechanism.

**5. Rollback is a single env flag, not a code revert.**
`OTEL_SDK_DISABLED=true` already short-circuits `init_observability()` to a no-op. If the Grafana Cloud integration misbehaves (e.g. unexpectedly high series cardinality, connectivity issues), ops can set that flag in `.env.prod` and redeploy — no code change needed to fully disable telemetry export.

## Risks / Trade-offs

- **[Metric cardinality exceeds free-tier 10k series]** → FastAPI/SQLAlchemy auto-instrumentation labels by route template and DB statement type, not raw values, so this is unlikely at current traffic; monitor active series count in Grafana Cloud's usage page after rollout and prune/relabel if it climbs.
- ~~[Outbound TLS/gRPC to Grafana Cloud blocked or flaky from Hetzner]~~ → **materialized and resolved during implementation**: Grafana Cloud's OTLP gateway doesn't support gRPC at all (confirmed with Grafana support, see Decision 3). Switched to the OTLP/HTTP exporters, which work correctly against the real gateway (verified with a live smoke test from dev, both traces and metrics exported with no errors).
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

- ~~Split the Basic Auth token into `GRAFANA_CLOUD_INSTANCE_ID` + `GRAFANA_CLOUD_API_TOKEN` secrets...~~ **Resolved:** single pre-encoded `GRAFANA_CLOUD_OTLP_HEADERS` secret (avoids base64-assembly logic in the deploy script's `envsubst` step).
- ~~Confirm the exact OTLP gateway hostname/port...~~ **Resolved:** it's an HTTP(S) URL, not a bare `host:port` (that assumption was gRPC-shaped and is now moot) — `https://otlp-gateway-<region>.grafana.net/otlp`, confirmed for `gb-south-1` as `https://otlp-gateway-prod-gb-south-1.grafana.net/otlp`. `init_observability` appends `/v1/traces` / `/v1/metrics` itself.
- Whether to also forward Celery worker/beat telemetry in this change or leave them uninstrumented for now — proposal scopes this to the four FastAPI services only; worker instrumentation can be a fast follow if desired.
