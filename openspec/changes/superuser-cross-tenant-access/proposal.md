## Why

The eventual goal is superuser access to any customer page — originally motivated by needing to configure AI settings (BYOK API keys) for prospects during sales demos without asking for their credentials or touching the DB directly. Extending cross-tenant read access one endpoint at a time (the earlier version of this change) doesn't scale to "any page" and doesn't cover writes at all. Session-level impersonation — a superuser picks a target `customer_id` and gets a token scoped to act as that customer — reuses the entire existing app (frontend + every service) unmodified, covering every current and future page for free, at the cost of building the impersonation mechanism once.

## What Changes

- Add a superuser-only endpoint to mint a short-lived **impersonation token**: superuser supplies a target `customer_id`, receives a token with admin-equivalent permissions scoped to that customer, but with `user_id` set to the superuser's own real identity (not borrowed from an existing user of that customer) — so every existing `created_by`/`updated_by` attribution in the app already reflects the true actor.
- Add a centralized audit hook in the shared `get_validated_user` dependency (`shared/security/dependencies.py`, used by every service): when a request carries an impersonation-flagged token, log it — method, path, target `customer_id`, actor, timestamp — to that service's own local `privileged_access_logs` table. Covers reads and writes uniformly, and can't be forgotten per-route since it's not opt-in.
- **BREAKING (internal only)**: fix `UserProviderKey` (`services/ai/app/models/user_provider_key.py`) to be looked up by `customer_id` instead of `user_id` — the existing "customer-scoped" claim in the frontend doesn't match the backend today. Needed for AI settings to behave correctly under an impersonation token (and fixes a pre-existing bug where two admins of the same org can silently shadow each other's key).
- Add a documented administrative-access policy disclosing that superusers may temporarily access any organization's account (read and write, as if logged in) for support/demo/compliance purposes, and that all such sessions are logged.

## Capabilities

### New Capabilities
- `customer-impersonation`: superuser mints a time-boxed session scoped to any customer, without needing that customer's credentials.
- `privileged-access-audit`: every request made under an impersonation session is logged with the true actor's identity, per-service, append-only.
- `ai-provider-settings`: BYOK API key/model configuration is scoped by `customer_id`, not by whichever individual user last saved it.

### Modified Capabilities
- `security-documentation`: administrative-access disclosure, updated to describe impersonation (not just read access).

## Impact

- **Code**: `shared/security/` (impersonation token issuance + shared audit hook), `services/users/` (impersonation endpoint, session table), every service's local DB (new `privileged_access_logs` table), `services/ai/app/models/user_provider_key.py` + `services/ai/app/crud/user_provider_key.py` + `services/ai/app/api/settings_routes.py` (customer_id keying fix).
- **Docs**: `docs/legal/privacy-policy-stub.md`, `SECURITY.md`.
- **Supersedes** the previous version of this change (parameter-driven per-endpoint `customer_id` overrides extended from the donor-grantee pattern to budget/report) — not needed once impersonation exists, since impersonated requests flow through the existing customer-scoped code paths unmodified. The existing donor-grantee superuser bypass (`_resolve_scoped_customer_id`) is left as-is, untouched by this change.
- **Frontend**: a customer-search picker in the top bar (`frontend-typescript/src/pages/Dashboard/TopBar.tsx`), visible only to superusers, plus a persistent, non-dismissible warning banner shown whenever impersonation is active. Otherwise the impersonated session uses the existing customer-facing app as-is — no other frontend changes.
