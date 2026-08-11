## Why

Some potential donors want grant reports and disbursement data to land in the CRM/grants platform they already run internally (Salesforce Nonprofit Cloud Grantmaking or Blackbaud Grantmaking) rather than requiring their staff to log into GrantFlow separately. Being able to offer this as a capability is a differentiator in donor conversations, but no integration code exists today — this proposal exists to scope the work so it can be evaluated and prioritized later, not to commit to building it now.

## What Changes

- Add a new `services/integrations` service that syncs GrantFlow budget/report data outward to a donor-org's connected CRM, opted in per donor-org.
- Add a provider-adapter registry (`ProviderAdapter` ABC + `@register`, mirroring `services/ai/app/services/provider.py`) with one adapter per CRM.
- Add an OAuth2 authorization-code client flow (redirect, callback route, token refresh job) — this does not exist anywhere in the codebase today; GrantFlow's current `OAuth2PasswordBearer` usage is only its own login scheme, not a client against a third party.
- Add encrypted per-donor-org credential storage for CRM OAuth tokens, modeled on `services/ai/app/models/user_provider_key.py`'s AES-GCM pattern.
- Add async sync jobs (Celery, via existing `services/worker` + RabbitMQ infra) that push `ReportModel`/`ReportLineModel`/`BudgetModel`/`BudgetLineModel` data to the connected CRM on report submission/review.
- **Salesforce Nonprofit Cloud Grantmaking**: build as Phase 1. Its Outbound Funds Module data model maps cleanly onto GrantFlow's schema (Funding Award / GAU Expenditure / Funding Award Requirement / Funding Disbursement correspond to Budget / BudgetLine+Category / Report / ReportLine), so this is scopeable now.
- **Blackbaud Grantmaking (SKY API)**: treat as a discovery spike only. Blackbaud's public docs describe the API as centered on top-line amounts, remaining balance, payment date/type — no confirmed line-item, category, or report-level surface. Real scope is unknown until a Blackbaud sandbox/developer account is obtained; do not commit to a build timeline until that discovery completes.

## Capabilities

### New Capabilities
- `donor-crm-sync`: OAuth2 connection management, provider-adapter registry, and outbound sync of budget/report/disbursement data to a donor-org's connected external CRM (Salesforce Nonprofit Cloud Grantmaking; Blackbaud Grantmaking scoped as discovery-only).

### Modified Capabilities
(none — this is purely additive; no existing capability's requirements change)

## Impact

- **New service**: `services/integrations` (FastAPI, own migrations, own DB tables for CRM connections/credentials/sync state).
- **New DB tables**: encrypted CRM credential store (per donor-org), sync-state/audit tracking.
- **Worker**: new Celery tasks in `services/worker` for async outbound sync and OAuth token refresh.
- **Budget service**: read-only consumer relationship — `services/budget` data is read (via internal REST, matching the existing `donor_grantee_client.py` cross-service pattern) by the new service; no changes to `services/budget` models required for Phase 1.
- **Frontend**: new donor-facing settings UI to connect/disconnect a CRM and view sync status (out of scope for Phase 1 discovery; only needed once Salesforce sync is built).
- **Gateway**: new route prefix needed in all three gateway configs (`nginx-dev.conf`, `nginx.conf`, `Caddyfile`) per this repo's existing "three gateway configs" gotcha.
- **Dependencies**: `simple-salesforce` or direct REST/OAuth2 client for Salesforce; no Blackbaud SDK dependency until discovery confirms feasibility.
