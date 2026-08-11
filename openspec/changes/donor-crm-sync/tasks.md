One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Foundation — service scaffold, OAuth2 client, encrypted credentials

- [ ] 1.1 Scaffold `services/integrations` FastAPI service (own `app/`, own Alembic migrations, own Dockerfile, wired into `docker-compose.local.yml`) following the `services/ai` layout.
- [ ] 1.2 Add `crm_connections` table (donor_org_id, provider, encrypted_access_token, encrypted_refresh_token, expires_at, status, last_synced_at) reusing the AES-GCM helper from `services/ai/app/utils/encryption.py`.
- [ ] 1.3 Build shared OAuth2 authorization-code client: authorize-redirect endpoint, callback route, token-refresh helper — parameterized per provider, not Salesforce-specific yet.
- [ ] 1.4 Wire the new service's route prefix into all three gateways (`nginx-dev.conf`, `nginx.conf`, `Caddyfile`) per this repo's known "three gateway configs" gotcha.
- [ ] 1.5 Run backend tests/lint clean for `services/integrations`; PR merged.

## 2. Salesforce connection management — depends on 1

- [ ] 2.1 Implement `ProviderAdapter` ABC + `@register` registry (mirroring `services/ai/app/services/provider.py`).
- [ ] 2.2 Implement `adapters/salesforce.py`: OAuth2 config (client id/secret, auth/token URLs), `test_connection()`.
- [ ] 2.3 Add connect/disconnect/status API endpoints on `services/integrations`, scoped to the calling user's donor org (reuse the org-scoping pattern from `services/budget/app/services/donor_grantee_client.py`).
- [ ] 2.4 Add minimal frontend "Connect Salesforce" settings UI (connect button → OAuth redirect, status badge, disconnect button) — no full UX polish, just a working flow.
- [ ] 2.5 Run backend + frontend tests/lint clean; manually verify a full connect → status "Connected" → disconnect cycle against a Salesforce developer/sandbox org; PR merged.

## 3. Salesforce outbound report sync — depends on 1, 2

- [ ] 3.1 Define field mapping: `BudgetModel`→Funding Award, `BudgetCategoryModel`/`BudgetLineModel`→GAU Expenditure/General Accounting Unit, `ReportModel`→Funding Award Requirement, `ReportLineModel`→Funding Disbursement.
- [ ] 3.2 Add Celery task in `services/worker` triggered on `ReportModel` status transition to `submitted`/`reviewed`, calling the Salesforce adapter to create/update the mapped records.
- [ ] 3.3 Record sync outcome (success/failure, timestamp, error detail) against the `crm_connections` row; on failure, do not block the in-app report-submission response.
- [ ] 3.4 Emit sync failures through the existing observability pipeline (Grafana Cloud OTLP) so failed syncs are visible without polling.
- [ ] 3.5 Handle token expiry mid-sync by invoking the refresh helper from group 1 before retrying once.
- [ ] 3.6 Run backend tests/lint clean; manually verify a report submission produces the expected Funding Disbursement/Requirement records in a Salesforce sandbox org; PR merged.

## 4. Blackbaud feasibility discovery spike — no code dependency on 1–3, can run in parallel

- [ ] 4.1 Obtain a Blackbaud SKY API developer/partner sandbox account with Grantmaking module access.
- [ ] 4.2 Determine whether the SKY API exposes report/line-item/category-level data, or only award-level totals (grant amount, remaining balance, payment date/type) as public docs suggest.
- [ ] 4.3 If line-item data is available, sketch a field mapping equivalent to group 3's Salesforce mapping and estimate build effort.
- [ ] 4.4 Write up findings and a go/no-go recommendation as a decision doc appended to this change (or a new `openspec/changes/donor-crm-sync-blackbaud` follow-up proposal if "go").
- [ ] 4.5 PR merged adding the findings doc to the repo (no application code required for a "no-go" outcome).
