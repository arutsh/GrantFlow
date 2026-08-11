## Context

GrantFlow currently has no outbound integration surface: `services/budget`'s `BudgetModel`/`BudgetLineModel`/`ReportModel`/`ReportLineModel`/`AttachmentModel` are only ever read by GrantFlow's own frontend over internal JSON REST. No PDF/CSV export, webhook, or third-party push exists anywhere in the codebase, and no prior code/docs/OpenSpec change references Blackbaud, Salesforce, or CRM sync — this is greenfield.

Two donor-org CRM targets are in scope for evaluation:
- **Salesforce Nonprofit Cloud Grantmaking** (built on the Outbound Funds Module): `Funding Award` / `GAU Expenditure` (→ `General Accounting Unit`) / `Funding Award Requirement` / `Funding Disbursement` map closely onto GrantFlow's `Budget` / `BudgetLine`+`BudgetCategory` / `Report` / `ReportLine`.
- **Blackbaud Grantmaking (SKY API)**: publicly documented as centered on top-line grant amount, remaining balance, payment date/type. No confirmed line-item, category-level, or requirement/report-level surface. Full schema is behind a Blackbaud developer/partner login not available during this proposal's research.

The nearest architectural precedents in-repo:
- `services/ai/app/services/provider.py`: `ABC` `ProviderAdapter` + `@register("name")` populating a module-level registry, with concrete adapters in `adapters/{anthropic,ollama}.py`. This is the intended shape for CRM adapters.
- `services/ai/app/models/user_provider_key.py` + `services/ai/app/utils/encryption.py`: AES-GCM encrypted per-user/per-customer credential storage. The right template for per-donor-org OAuth token storage (vs. the current email-provider pattern of global env-var secrets, which doesn't fit per-org creds).
- `services/budget/app/services/donor_grantee_client.py`: existing pattern for one service calling another over internal REST to check org-scoped relationships — reusable for the new service reading budget/report data it doesn't own.

## Goals / Non-Goals

**Goals:**
- Produce a build-ready plan for a Salesforce Nonprofit Cloud Grantmaking sync that the team can pick up without further scoping.
- Produce a bounded discovery plan for Blackbaud SKY API that resolves the schema unknowns before any commitment to build.
- Keep the design opt-in and additive: no existing service's data model changes.

**Non-Goals:**
- Building Blackbaud sync itself — only discovery is in scope until findings justify a follow-up proposal.
- Two-way sync (pulling CRM changes back into GrantFlow) — Phase 1 is outbound-only (GrantFlow → CRM).
- A generic "integrations platform" for arbitrary CRMs beyond these two named targets.
- Donor-facing UI polish — a minimal connect/disconnect/status view is enough to validate the flow end-to-end; full UX is a later pass.

## Decisions

**New standalone `services/integrations` service, not a module inside `services/budget`.**
Mirrors the existing per-domain service boundary (`services/ai`, `services/chat`, etc.) and keeps OAuth-credential handling and outbound network calls to third parties isolated from the budget service's transactional core. Alternative considered: add sync logic directly into `services/budget`'s worker tasks — rejected because it would mix budget's core CRUD/audit responsibilities with third-party credential handling and retry/backoff logic that has a different failure profile.

**Provider adapter registry, copied from `services/ai/app/services/provider.py`.**
`ProviderAdapter` ABC with `sync_report(report, config)` / `test_connection(config)` methods, `@register("salesforce")` / `@register("blackbaud")`. Keeps CRM-specific field mapping isolated per adapter and matches an already-reviewed pattern in the codebase rather than inventing a new one.

**OAuth2 authorization-code flow, built once and shared across both adapters.**
Both Salesforce and Blackbaud support OAuth2 authorization-code grants. A single `oauth_client.py` (authorize-redirect, callback route, refresh-token job) parameterized per provider avoids duplicating token-refresh/retry logic. Alternative considered: Salesforce JWT-bearer flow (no user redirect, better for server-to-server) — deferred; authorization-code is simpler to reason about for a donor-org self-serve "Connect your CRM" flow and works for both providers, so it's the shared default. JWT-bearer can be added later per-org if a donor requires it.

**Encrypted credential table modeled on `user_provider_key`, scoped by `donor_org_id` not `user_id`.**
CRM connections belong to the donor organization, not an individual user — multiple users at a donor org should see the same connection status. New table `crm_connections` (donor_org_id, provider, encrypted_access_token, encrypted_refresh_token, expires_at, status) using the same AES-GCM helper from `services/ai/app/utils/encryption.py`.

**Outbound sync triggered by report lifecycle events, run as Celery tasks via existing `services/worker` + RabbitMQ.**
Sync fires on report submission/review transitions (matching Salesforce's `Funding Award Requirement` gating a `Funding Disbursement`), not on every field edit — reduces API call volume and gives a natural retry boundary. Uses existing worker infra rather than introducing a new queue/scheduler.

**Blackbaud is discovery-only in this proposal.**
Because the public SKY API docs don't confirm line-item or report-level access, committing to an adapter now risks building against a schema that doesn't support the required granularity. Discovery tasks (below) produce a go/no-go and, if "go," a follow-up proposal scoped like Salesforce's.

## Risks / Trade-offs

- **[Risk]** Blackbaud SKY API may not expose report/line-item-level data at all, only top-line amounts → **Mitigation**: discovery spike with a sandbox account is a hard gate before any Blackbaud adapter work is scheduled; proposal explicitly does not commit to a Blackbaud build.
- **[Risk]** OAuth2 token refresh failures (revoked donor-org access, expired refresh tokens) could silently stop sync → **Mitigation**: `crm_connections.status` surfaces connection health; failed syncs alert via existing audit-log/observability pipeline (Grafana Cloud OTLP) rather than failing silently.
- **[Risk]** Field-mapping drift — Salesforce org customizations (custom GAU categories, renamed fields) vary per donor-org → **Mitigation**: Phase 1 targets the standard Nonprofit Cloud Grantmaking object model only; custom-field mapping is out of scope until a real donor integration surfaces the need.
- **[Trade-off]** Authorization-code flow requires a donor-org admin to complete an OAuth consent screen — more friction than an API-key paste, but necessary since both platforms require it for org-scoped access; no simpler alternative exists for either provider.

## Migration Plan

Purely additive — new service, new tables, no changes to existing services' schemas. Rollout is per donor-org opt-in (a donor-org with no `crm_connections` row is entirely unaffected). Rollback is deleting/disabling the `services/integrations` deployment; no data migration or backfill is required since sync is outbound-only and CRM-side data is not read back.

## Open Questions

- Does Blackbaud SKY API's Grantmaking product expose report/line-item-level fields, or only award-level totals? (Resolved by the discovery spike in tasks.md.)
- Should Phase 1 support Salesforce JWT-bearer flow for donor-orgs that prefer server-to-server auth over authorization-code, or is authorization-code sufficient for all early adopters?
- What triggers re-sync if a report is reopened after submission (`ReportStatus` supports `reopen`) — resend as an update, or treat as a new sync event?
