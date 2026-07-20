# Tasks

Workflow rule: **one group = one GitHub ticket = one PR, merged before the next group starts.** Branch names are fixed per ticket. Every PR: `flake8 --max-line-length=100` clean; commits/pushes only with explicit user approval.

## 1. Shared observability module — ticket #129 (`Shared/Issue-129/otlp-tls-header-auth`)

- [ ] 1.1 Update `shared/observability/__init__.py` so `init_observability()` derives `insecure` from an env flag/endpoint instead of hardcoding `insecure=True`
- [ ] 1.2 Read `OTEL_EXPORTER_OTLP_HEADERS` and pass it as `headers=` to both `OTLPSpanExporter` and `OTLPMetricExporter`
- [ ] 1.3 Verify the `OTEL_SDK_DISABLED` no-op bail-out and local-dev defaults (`insecure=True`, `localhost:4317`) still work unchanged when no Grafana Cloud env vars are set
- [ ] 1.4 Add/extend `shared/tests/` coverage for both branches (insecure-default, TLS+headers) plus the disabled bail-out
- [ ] 1.5 PR merged

## 2. Production wiring, secrets, deploy, verification — ticket #130 (`Platform/Issue-130/grafana-cloud-prod-wiring`)

- [ ] 2.1 Create (or reuse) a Grafana Cloud org and free-tier stack; note the OTLP gateway endpoint hostname/port for the chosen region
- [ ] 2.2 Generate a scoped Grafana Cloud API token/access policy with traces + metrics write permission
- [ ] 2.3 Decide secret shape (single pre-encoded `GRAFANA_CLOUD_OTLP_HEADERS` vs. split `GRAFANA_CLOUD_INSTANCE_ID` + `GRAFANA_CLOUD_API_TOKEN`) and add the chosen secrets to the GitHub repo's Actions secrets
- [ ] 2.4 Add placeholder vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, TLS flag) to `.env.prod` template as `${VAR}` references
- [ ] 2.5 Add the same placeholder vars to each `services/{users,budget,ai,chat}/.env.*.prod` template
- [ ] 2.6 Update `.github/workflows/deploy.yml`'s env-file regeneration step to populate the new vars from the secrets added in 2.3
- [ ] 2.7 Confirm no real endpoint/token value is ever committed — templates only contain `${VAR}` placeholders
- [ ] 2.8 Deploy to production (push to `main` or manual `workflow_dispatch`)
- [ ] 2.9 Send at least one real request to each of the four services and confirm a matching trace appears in Grafana Cloud's trace search, tagged with the correct `service.name`
- [ ] 2.10 Confirm metrics are arriving in Grafana Cloud and check the active series count against the 10k free-tier budget
- [ ] 2.11 Test the rollback path: set `OTEL_SDK_DISABLED=true` in `.env.prod`, redeploy, confirm no OTLP export calls are made, then re-enable
- [ ] 2.12 PR merged

## 3. Dashboard and docs — ticket #131 (`Platform/Issue-131/grafana-cloud-dashboard-docs`)

- [ ] 3.1 Build a Grafana Cloud dashboard with per-service panels for request rate, error rate, and p95/p99 latency; check its JSON export into the repo (e.g. `monitoring/grafana-cloud/dashboard.json`)
- [ ] 3.2 Verify all four services render non-empty panels after sending traffic
- [ ] 3.3 Add a new prod observability doc under `docs/observability/` describing the Grafana Cloud setup, env vars, and how to view traces/metrics/dashboard
- [ ] 3.4 Update `docs/deployment/DEPLOYMENT_MODES.md`'s production section to reference where telemetry goes and link the new doc
- [ ] 3.5 PR merged
