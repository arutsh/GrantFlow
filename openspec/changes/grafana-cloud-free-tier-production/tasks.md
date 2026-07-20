## 1. Grafana Cloud provisioning

- [ ] 1.1 Create (or reuse) a Grafana Cloud org and free-tier stack; note the OTLP gateway endpoint hostname/port for the chosen region
- [ ] 1.2 Generate a scoped Grafana Cloud API token/access policy with traces + metrics write permission
- [ ] 1.3 Decide secret shape (single pre-encoded `GRAFANA_CLOUD_OTLP_HEADERS` vs. split `GRAFANA_CLOUD_INSTANCE_ID` + `GRAFANA_CLOUD_API_TOKEN`) and add the chosen secrets to the GitHub repo's Actions secrets

## 2. Shared observability module

- [ ] 2.1 Update `shared/observability/__init__.py` so `init_observability()` derives `insecure` from an env flag/endpoint scheme instead of hardcoding `insecure=True`
- [ ] 2.2 Update `init_observability()` to read `OTEL_EXPORTER_OTLP_HEADERS` and pass it as `headers=` to both `OTLPSpanExporter` and `OTLPMetricExporter`
- [ ] 2.3 Verify the `OTEL_SDK_DISABLED` no-op bail-out and local-dev defaults (`insecure=True`, `localhost:4317`) still work unchanged when no Grafana Cloud env vars are set

## 3. Production configuration

- [ ] 3.1 Add placeholder vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, TLS flag) to `.env.prod` template as `${VAR}` references
- [ ] 3.2 Add the same placeholder vars to each `services/{users,budget,ai,chat}/.env.*.prod` template
- [ ] 3.3 Update `.github/workflows/deploy.yml`'s env-file regeneration step to populate the new vars from the GitHub Actions secrets added in 1.3
- [ ] 3.4 Confirm no real endpoint/token value is ever committed — templates only contain `${VAR}` placeholders

## 4. Rollout and verification

- [ ] 4.1 Deploy to production (push to `main` or manual `workflow_dispatch`)
- [ ] 4.2 Send at least one real request to each of the four services and confirm a matching trace appears in Grafana Cloud's trace search, tagged with the correct `service.name`
- [ ] 4.3 Confirm metrics are arriving in Grafana Cloud and check the active series count against the 10k free-tier budget
- [ ] 4.4 Test the rollback path: set `OTEL_SDK_DISABLED=true` in `.env.prod`, redeploy, confirm no OTLP export calls are made, then re-enable

## 5. Dashboard

- [ ] 5.1 Build (or import) a Grafana Cloud dashboard with per-service panels for request rate, error rate, and p95/p99 latency
- [ ] 5.2 Verify all four services render non-empty panels after sending traffic

## 6. Documentation

- [ ] 6.1 Add a new prod observability doc under `docs/observability/` describing the Grafana Cloud setup, env vars, and how to view traces/metrics/dashboard
- [ ] 6.2 Update `docs/deployment/DEPLOYMENT_MODES.md`'s production section to reference where telemetry goes and link the new doc
