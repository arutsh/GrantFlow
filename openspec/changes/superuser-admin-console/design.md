## Context

`services/users` owns `CustomerModel` and `UserModel`; `services/ai` owns `CustomerAIDefaults` (the platform-fallback flag, via `set_platform_fallback`/`get_customer_ai_defaults` in `services/ai/app/crud/customer_ai_defaults.py`, exposed today only through `PUT /platform-fallback` in `services/ai/app/api/settings_routes.py`, which derives `customer_id` from the caller's token via `resolve_customer_id(valid_user)`). Today's only cross-tenant channel is impersonation (`customer-impersonation` capability): a superuser mints a token scoped to one target `customer_id` and everything downstream — including that platform-fallback route — trusts the token's `customer_id`, never a request parameter. Privileged access is logged only for requests carrying an impersonation token (`privileged-access-audit`).

Per the user's decision, this change adds a small set of superuser-only endpoints that accept `customer_id`/`user_id` explicitly, so the console can list and toggle across all tenants without impersonating each one first.

## Goals / Non-Goals

**Goals:**
- Superuser-only `/admin` page: customer list (name, country, is_ngo/is_donor, currency, deactivated status, platform-fallback enabled) with an inline platform-fallback toggle.
- Superuser-only user list (name, email, customer, role, status) with inline role/admin-status update.
- New endpoints scoped tightly to these actions, each independently superuser-gated and each logged as privileged access even though no impersonation token is involved.

**Non-Goals:**
- Inviting, removing, or editing company details for another company — those stay impersonation-only (`company-user-administration`, `superuser-tenant-administration`), unchanged by this change.
- Deactivating a company from this console — `superuser-tenant-administration` already gives superusers a direct deactivate path; out of scope to duplicate here unless the user wants it added to the same list view later.
- Pagination/filtering/search polish, bulk actions, CSV export — first cut is "very simple list" per the user's framing.
- Editing a customer's `is_ngo`/`is_donor`/currency/name from this console — display-only here; editing those already exists via `company-user-administration` (impersonation).

## Decisions

**1. New direct superuser endpoints, not implicit impersonation.** Confirmed with the user. `PUT /users/admin/customers/{customer_id}` is not proposed; instead:
- `GET /users/admin/customers` — list all customers (superuser only).
- `GET /users/admin/users` — list all users across all customers (superuser only).
- `PUT /users/admin/users/{user_id}/role` — update a user's role/admin status by id (superuser only).
- `PUT /ai/admin/customers/{customer_id}/platform-fallback` — toggle platform-fallback by explicit `customer_id` (superuser only), alongside the existing impersonation-scoped `PUT /platform-fallback`.

Each handler checks `role == "superuser"` directly (no `customer_id` resolution from the token at all) — mirrors the existing `_require_superuser` pattern in `settings_routes.py`, just without the `resolve_customer_id` step. Alternative considered: route everything through a server-side "shadow impersonation" (mint and immediately use a token) to reuse existing customer-scoped endpoints unchanged — rejected per the user's explicit choice, since it adds impersonation-session churn and audit noise for what should read as a single direct action.

**2. Two backend services, one frontend page.** Customer list/platform-fallback endpoints split across `services/users` (customer/user data) and `services/ai` (platform-fallback flag) — same split as the data already lives in today. The frontend `/admin` page calls both APIs and merges by `customer_id`, the same pattern `AiIntegrationsSection.tsx` already uses for provider settings. Alternative (a single "admin" aggregation endpoint in one service) was considered and rejected — would require one service to reach into another's DB or make a synchronous cross-service call, which the codebase avoids elsewhere (services trust JWT claims, not each other's data).

**3. Extend `privileged-access-audit` to cover these direct actions.** Since these endpoints don't carry an impersonation token, they fall outside today's "logged whenever the request uses an impersonation token" requirement. Each new admin-console write endpoint (platform-fallback toggle, role update) explicitly writes a `privileged_access_logs` entry itself, same shape as the impersonation-triggered ones (actor, target `customer_id`/`user_id`, request, timestamp). The two `GET` list endpoints are not logged as privileged access, consistent with how impersonation's own read requests are already logged — actually, the impersonation spec logs reads too (see its "A view performed during impersonation is logged" scenario); for consistency the list endpoints SHOULD be logged as well. Left as an open question below rather than silently deciding either way.

**4. Role/admin-status update reuses `company-user-administration`'s last-admin protection.** `PUT /users/admin/users/{user_id}/role` calls the same guarded path `update_user_role_service` already uses (last-admin quorum check, row locking) rather than a raw field write, so a superuser can't accidentally leave a company with zero admins any more than a company's own admin could.

**5. Gateway wiring.** New routes need adding to all three gateway configs per [[project_three_gateway_configs]] — `nginx-dev.conf`, `nginx.conf`, and `Caddyfile` — under the existing `/api/v1/users/` and `/api/v1/ai/` prefixes (no new top-level prefix needed, since `/admin/...` sits under each service's existing route tree).

## Risks / Trade-offs

- [Two new superuser-only endpoint families instead of one] → deliberate, matches existing service-per-domain boundaries; frontend hides the seam.
- [Explicit customer_id/user_id params reopen the "superuser has no cross-tenant access outside impersonation" guarantee the codebase otherwise holds everywhere] → mitigated by keeping the exception to exactly these four endpoints, each independently superuser-gated and audit-logged; every other cross-tenant surface is untouched.
- [Two ways to set platform-fallback now exist — impersonation-scoped `PUT /platform-fallback` and the new by-id route] → both call the same `set_platform_fallback` CRUD function, so behavior can't drift; documented as intentional dual entry point, not duplication to clean up.
- [`GET /users/admin/users` returns every user across every tenant in one response] → fine at current scale (nonprofit-platform user counts), but has no pagination; flagged as a known limitation, not blocking for a first cut.

## Migration Plan

No data migration. Additive endpoints and a new frontend route; nothing existing changes shape. Rollback is deleting the new route/nav entry and endpoints.

## Open Questions

- Should the two `GET` list endpoints also write `privileged_access_logs` entries (matching how impersonation logs reads, not just writes), or only the two write actions? Leaning toward logging both for consistency, but confirm before tasks.md locks it in.
- Should company deactivation (already superuser-direct per `superuser-tenant-administration`) be surfaced as an action on this same customer list row in a later iteration, or does that stay a separate flow?
