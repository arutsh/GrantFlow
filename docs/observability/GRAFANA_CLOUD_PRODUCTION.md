# Production Observability — Grafana Cloud

Production traces and metrics are exported directly from each service to a
hosted Grafana Cloud free-tier stack. No collector, Jaeger, Prometheus, or
Grafana container runs on the production box — that stack (see
[MONITORING_SETUP.md](MONITORING_SETUP.md)) exists only in dev, where it was
already judged too heavy for the 4GB Hetzner server.

## How it works

All four production FastAPI services (`users`, `budget`, `ai`, `chat`) call
`init_observability(service_name)` from `shared/observability/__init__.py` at
startup. That function is entirely config-driven — the four `main.py` call
sites never changed:

- **Transport**: OTLP/HTTP (protobuf), not gRPC. Grafana Cloud's OTLP gateway
  does not accept gRPC at all, in any region — its fronting proxy is
  HTTP/1.1-only and never negotiates ALPN for `h2`, so a gRPC client's TLS
  handshake is refused before any request is sent. Confirmed both by testing
  directly against the production gateway and with Grafana support. `init_observability`
  appends `/v1/traces` / `/v1/metrics` to the base endpoint itself.
- **Endpoint**: `OTEL_EXPORTER_OTLP_ENDPOINT` — Grafana Cloud's OTLP gateway
  base URL for the provisioned stack, e.g.
  `https://otlp-gateway-prod-gb-south-1.grafana.net/otlp` (the exact hostname
  depends on the stack's region — find it under Connections → Collector
  Setup → OpenTelemetry, or the stack's Details page). Unset or pointed at
  `localhost:4318` (dev's default, the local OTel Collector's HTTP receiver
  port), traces/metrics go to the local OTel Collector exactly as before.
- **Auth**: `OTEL_EXPORTER_OTLP_HEADERS` — a Basic Auth header
  (`authorization=Basic <base64(instance_id:api_token)>`) issued by Grafana
  Cloud's access policy for the stack. Unset in dev, so no auth is sent
  locally. Note the value is `base64(instance_id:token)`, not the raw API
  token by itself — a raw token pasted in directly will authenticate as
  nothing and get a 401.
- **TLS**: derived automatically by the exporter from the endpoint's
  `http://` vs `https://` scheme — no separate flag needed.
- **Kill switch**: `OTEL_SDK_DISABLED=true` makes `init_observability()` a
  no-op — no exporters are constructed and no OTLP calls are made. This is
  the rollback path if the Grafana Cloud integration misbehaves; no code
  change or revert needed, just set the flag and redeploy.

## Where the values come from

`OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` are set in
each of `services/{users,budget,ai,chat}/.env.*.prod` as `${GRAFANA_CLOUD_OTLP_ENDPOINT}`
/ `${GRAFANA_CLOUD_OTLP_HEADERS}` placeholders — never a real value in the
committed template. `.github/workflows/deploy.yml`'s env-file regeneration
step substitutes the real values from the `GRAFANA_CLOUD_OTLP_ENDPOINT` and
`GRAFANA_CLOUD_OTLP_HEADERS` GitHub Actions secrets in place on the server at
deploy time, the same way `JWT_SECRET_KEY` and the other prod secrets already
work.

Provisioning the Grafana Cloud org/stack, generating the scoped API token,
and setting those two secrets is a one-time manual step done outside this
repo (Grafana Cloud console + `gh secret set` / repo Settings → Secrets).

## Viewing traces and metrics

Log into the Grafana Cloud stack and use:

- **Explore → Tempo** (or the trace search view) — filter by `service.name`
  (`users`, `budget`, `ai`, `chat`) to find traces for a given service.
- **Explore → Prometheus/Mimir** — query the auto-instrumented FastAPI/SQLAlchemy
  metrics (request rate, duration histograms, DB query spans).
- **Dashboards** — the starter dashboard (request rate, error rate, p95/p99
  latency per service) is checked into
  [`monitoring/grafana-cloud/dashboard.json`](../../monitoring/grafana-cloud/dashboard.json)
  and importable via Grafana Cloud's dashboard JSON import.

## Free-tier limits

The free tier caps at 10k active metric series and 50GB traces/month with
14-day retention. FastAPI/SQLAlchemy auto-instrumentation labels by route
template and statement type, not raw values, so series count should stay
well under the cap at this app's traffic — check the usage page in Grafana
Cloud after rollout if that assumption ever needs revisiting.

## Out of scope

Application logs are not shipped to Grafana Cloud Loki — prod logs stay on
`docker logs` for now (see [DEPLOYMENT_MODES.md](../deployment/DEPLOYMENT_MODES.md)).
Alerting rules are not configured. Both are noted as future follow-ons, not
covered by this setup.
