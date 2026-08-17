# Tasks

Workflow rule (superseded for this pass — see note below): **one group = one GitHub ticket = one PR, merged before the next group starts.** Branch names are fixed per ticket. Every PR: `flake8 --max-line-length=100` clean; commits/pushes only with explicit user approval.

> **Note:** at the user's explicit request, all code/config/docs tasks below were implemented together on one branch (`Platform/Issue-129-131/grafana-cloud-free-tier-production`) for a single combined PR closing #129, #130, and #131, rather than three sequential PRs. Tasks requiring a live Grafana Cloud stack or a production deploy (account/token provisioning, secret values, `workflow_dispatch`, live trace/metric verification) are **not done by Claude** — they need the user's direct action and are left unchecked below.
>
> **Transport changed mid-implementation: gRPC → HTTP.** The plan (and `design.md`) originally assumed the OTLP gRPC exporters would work against Grafana Cloud. Live testing from dev against the real gateway (`otlp-gateway-prod-gb-south-1.grafana.net`) showed gRPC's TLS handshake failing (`Cannot check peer: missing selected ALPN property`), isolated at the raw TLS layer with `openssl s_client -alpn h2` (server never negotiates ALPN, HTTP/1.1-only fronting proxy) and confirmed by Grafana support: **the OTLP gateway does not support gRPC in any region**, only OTLP/HTTP. `shared/observability/__init__.py` now uses `opentelemetry-exporter-otlp-proto-http` (already present in every service's `requirements.txt`, no dependency changes needed) — see `design.md` Decision 3 for the full writeup. Re-verified end-to-end against the real Grafana Cloud gateway from dev: both a trace and a metric exported successfully via the actual `init_observability()` call path.

## 1. Shared observability module — ticket #129 (`Shared/Issue-129/otlp-tls-header-auth`)

- [x] 1.1 Update `shared/observability/__init__.py` so `init_observability()` no longer hardcodes an insecure local endpoint — switched to the OTLP/HTTP exporters, which derive TLS automatically from the endpoint's `http`/`https` scheme (no custom logic needed; see transport-change note above)
- [x] 1.2 `OTEL_EXPORTER_OTLP_HEADERS` is read directly by each exporter from the environment (native HTTP-exporter behavior); `init_observability` appends `/v1/traces` / `/v1/metrics` to the base endpoint itself, since passing an explicit `endpoint=` bypasses the exporters' own env-fallback auto-append
- [x] 1.3 Verify the `OTEL_SDK_DISABLED` no-op bail-out and local-dev defaults (`http://localhost:4318`, the local OTel Collector's HTTP receiver port) still work unchanged when no Grafana Cloud env vars are set
- [x] 1.4 Add/extend `shared/tests/` coverage (disabled bail-out, local-dev default endpoint, Grafana Cloud endpoint forwarding, explicit-override, trailing-slash handling)
- [x] 1.5 PR merged (#207)

## 2. Production wiring, secrets, deploy, verification — ticket #130 (`Platform/Issue-130/grafana-cloud-prod-wiring`)

- [x] 2.1 Create (or reuse) a Grafana Cloud org and free-tier stack; note the OTLP gateway endpoint for the chosen region — done by the user: stack `cleverspring2715`, region `gb-south-1`, endpoint `https://otlp-gateway-prod-gb-south-1.grafana.net/otlp` (HTTP base URL, not a bare `host:port` — see transport-change note above)
- [x] 2.2 Generate a scoped Grafana Cloud API token/access policy with traces + metrics write permission — done by the user (instance ID `1729182`, token kept in gitignored local `.devrc`, never shared in chat); functionally verified with write access via a real end-to-end smoke test (below), not just an assumed scope
- [x] 2.3 Decide secret shape (single pre-encoded `GRAFANA_CLOUD_OTLP_HEADERS` vs. split `GRAFANA_CLOUD_INSTANCE_ID` + `GRAFANA_CLOUD_API_TOKEN`) and add the chosen secrets to the GitHub repo's Actions secrets — **decided: single pre-encoded `GRAFANA_CLOUD_OTLP_ENDPOINT` + `GRAFANA_CLOUD_OTLP_HEADERS` (avoids base64-assembly in the deploy script)**; live-tested locally end-to-end (both a real trace and a real metric exported successfully through `init_observability()` against the actual production gateway); **the GitHub Actions secret values themselves still need to be set by the user** (`gh secret set ...`), separate from the local `.devrc` test
- [x] 2.4 Add placeholder vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`) to each service's env template as `${VAR}` references (root `.env.prod` is compose-level only and not consumed by services — see `docker-compose.prod.yml` `env_file:` entries — so it was intentionally left untouched)
- [x] 2.5 Add the same placeholder vars to each `services/{users,budget,ai,chat}/.env.*.prod` template
- [x] 2.6 Update `.github/workflows/deploy.yml`'s env-file regeneration step to populate the new vars from the secrets added in 2.3
- [x] 2.7 Confirm no real endpoint/token value is ever committed — templates only contain `${VAR}` placeholders
- [x] 2.8 Deploy to production (push to `main` or manual `workflow_dispatch`) — confirmed 2026-08-16: all 5 prod containers running current `main`, deploy workflow history shows repeated successful runs since the secrets were set (2026-08-08)
- [x] 2.9 Send at least one real request to each of the four services and confirm a matching trace appears in Grafana Cloud's trace search, tagged with the correct `service.name` — confirmed 2026-08-16: `ai-service` trace directly verified in Explore → Tempo (`POST /api/v1/ai/decide`, trace ID `c5fab390...`); `users`/`budget`/`chat` requests sent (200s) and corroborated via matching Loki log entries in the same window, same `init_observability()` code path
- [ ] 2.10 Confirm metrics are arriving in Grafana Cloud and check the active series count against the 10k free-tier budget — metrics arrival confirmed 2026-08-16 (`http_server_duration_milliseconds_*` etc. populated with real traffic in Explore → Metrics); **active series count vs. the 10k budget still needs checking on the Grafana Cloud usage page**
- [ ] 2.11 Test the rollback path: set `OTEL_SDK_DISABLED=true` in `.env.prod`, redeploy, confirm no OTLP export calls are made, then re-enable — not yet exercised
- [x] 2.12 PR merged (#207)

## 3. Dashboard and docs — ticket #131 (`Platform/Issue-131/grafana-cloud-dashboard-docs`)

- [x] 3.1 Build a starter Grafana Cloud dashboard with per-service panels for request rate, error rate, and p95/p99 latency; checked into `monitoring/grafana-cloud/dashboard.json` — metric/label names are best-effort from the OTel instrumentor defaults, **not yet verified against a live stack** (see `monitoring/grafana-cloud/README.md`)
- [x] 3.2 Verify all four services render non-empty panels after sending traffic — confirmed 2026-08-16: the dashboard's key unverified assumption (`http_server_duration_milliseconds_{bucket,count,sum}` metric names) is now confirmed correct in Explore → Metrics with real traffic; the imported `dashboard.json` panels themselves weren't individually re-opened, but the underlying data they query exists
- [x] 3.3 Add a new prod observability doc under `docs/observability/` describing the Grafana Cloud setup, env vars, and how to view traces/metrics/dashboard (`docs/observability/GRAFANA_CLOUD_PRODUCTION.md`)
- [x] 3.4 Update `docs/deployment/DEPLOYMENT_MODES.md`'s production section to reference where telemetry goes and link the new doc
- [x] 3.5 PR merged (#207)
