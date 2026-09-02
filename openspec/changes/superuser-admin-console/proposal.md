## Why

Superusers currently have no direct view across all customers and users — the only cross-tenant channel is impersonating one customer at a time via the top-bar picker (`ImpersonatePicker.tsx`), which is built for "act as this company," not "survey everything." Quick operational tasks (checking who has platform-AI-fallback enabled, fixing a stuck admin status) require impersonating a specific company first, which is slow when the superuser doesn't yet know which company needs attention.

## What Changes

- New `/admin` route in the frontend, visible only to `role: superuser`, with a nav entry gated the same way `ImpersonatePicker` is gated today.
- Customer list view: table of all customers (name, country, `is_ngo`/`is_donor`, currency, deactivated status, platform-AI-fallback enabled/disabled) with an inline toggle to enable/disable platform-AI-fallback for any customer directly.
- User list view: table of all users across all customers (name, email, customer, role, status) with inline controls to view details and update role/admin status directly.
- **BREAKING (spec-level, not runtime):** carves out a narrow, explicit exception to `customer-impersonation`'s "no cross-tenant access outside an active impersonation session" rule — new superuser-only endpoints that take `customer_id`/`user_id` explicitly, scoped to exactly these list-and-toggle actions. All existing impersonation-based flows (invite/remove/promote within a company, company detail edits) are unchanged and still impersonation-only.
- New backend endpoints (service TBD in design.md): list all customers, list all users, toggle a customer's platform-AI-fallback default by `customer_id`, update a user's role/admin status by `user_id` — each independently superuser-gated, each attributed to the superuser's real identity in audit logs.

## Capabilities

### New Capabilities
- `superuser-admin-console`: superuser-only `/admin` page(s) listing all customers and all users, with direct (non-impersonation) read access and narrowly-scoped write actions (platform-AI-fallback toggle, user role/admin-status update).

### Modified Capabilities
- `customer-impersonation`: the "no cross-tenant data access outside an active impersonation session" requirement gains an explicit, narrow exception for the new superuser-admin-console list/toggle endpoints — everything else about that requirement (list/detail endpoints for budgets, reports, etc.) is unchanged.
- `ai-provider-settings`: adds a superuser-only way to set/unset a customer's platform-AI-fallback default by explicit `customer_id`, alongside the existing impersonation-scoped `PUT /platform-fallback` route (which resolves `customer_id` from the token and stays as-is for admins acting within their own impersonated session).
- `superuser-tenant-administration`: today states "no dedicated superuser-scoped endpoints exist" for company/user administration (impersonation is the only channel) — this change adds the first ones, scoped strictly to read (list) and the two toggles above. Invite/remove/promote-within-company and company detail edits remain impersonation-only and out of scope here.
- `privileged-access-audit`: today's requirement logs a `privileged_access_logs` entry only for requests made *using an impersonation token*. The new admin-console endpoints are called with the superuser's own direct token (no impersonation session), so they need an explicit extension of this requirement to also log direct cross-tenant superuser actions, not just impersonation-token requests.

## Impact

- `services/users`: new superuser-gated list-customers / list-users endpoints, new update-user-role-by-id endpoint.
- `services/ai`: new superuser-gated set-platform-fallback-by-customer-id endpoint (or extend existing route to accept an optional `customer_id` for superusers).
- `frontend-typescript`: new `/admin` route + nav entry, new page(s) under `src/pages/Admin/` (or similar), new API client methods, `AuthContext`/routing gate on `role === "superuser"`.
- `privileged-access-audit`: these new cross-tenant actions should be logged the same way impersonation-derived actions are, since they bypass the impersonation session entirely.
