Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Close superuser blanket cross-tenant access in budget/report

- [x] 1.1 Remove the `if valid_user["role"] == "superuser": <unscoped>` branch in `services/budget/app/services/budget_services.py::list_budget_service`; always call `list_budgets(db, customer_id=valid_user.get("customer_id"))`, returning an empty list when `customer_id` is absent
- [x] 1.2 Remove the equivalent branches in `budget_services.py::get_budget_service`, `_resolve_updatable_budget`, `_can_view_budget`/`get_viewable_budget_service` — scope purely by `valid_user.get("customer_id")`, treating its absence as not-found
- [x] 1.3 Remove the equivalent branches in `services/budget/app/services/budget_line_services.py` (`get_viewable_budget_lines_service`, `get_budget_lines_service`, `get_budget_line_by_id_service`) — also `create_budget_line_service`, same bypass shape, found during implementation
- [x] 1.4 Remove the equivalent branch in `services/budget/app/services/report_services.py` (`get_viewable_budget`/`_get_budget_or_404`) — also `is_owner`, `_can_review`, `list_all_reports_service`, same bypass shape, found during implementation
- [x] 1.5 Tests: a superuser token with no `customer_id` gets an empty list from every list endpoint touched above, and not-found from every single-resource endpoint touched above; a regular customer's own access is unaffected
- [x] 1.6 Run budget-service test suite and flake8 (`--max-line-length=100`) clean; PR merged

## 2. Fix AI provider settings to be customer-scoped

- [x] 2.1 Add migration `services/ai/migrations/versions/` adding a unique/lookup index on `UserProviderKey.customer_id` (per provider), and a data-migration note for any existing rows (dev/demo data only at this stage — no production backfill concern yet)
- [x] 2.2 Change `services/ai/app/crud/user_provider_key.py`'s `get_key`/`upsert_key`/`delete_key` to key by `customer_id` instead of `user_id`
- [x] 2.3 Update `services/ai/app/api/settings_routes.py` (`get_ai_settings`/`save_ai_settings`/`clear_ai_key`) to resolve and pass `customer_id` (via existing `resolve_customer_id`) instead of `user_id` to the CRUD functions
- [x] 2.4 Update/add tests: two different admin-role users of the same customer see and modify the same AI settings row
- [x] 2.5 Run ai-service test suite and flake8 (`--max-line-length=100`) clean; PR merged

## 3. Impersonation token issuance — depends on 1

- [ ] 3.1 Add `impersonation_sessions` (or fold into `privileged_access_logs`, see Group 4) tracking in `services/users` if session bookkeeping beyond the JWT itself is needed (e.g. for revocation) — decide during implementation per design.md's open question on TTL
- [ ] 3.2 Add superuser-only endpoint in `services/users` to mint an impersonation token: accepts target `customer_id`, issues a token with admin-equivalent permissions scoped to that customer, `user_id` set to the superuser's own real id, and an impersonation flag/claim
- [ ] 3.3 Set a short, fixed expiry on impersonation tokens (see design.md open question for TTL value)
- [ ] 3.4 Tests: superuser can mint a token for any `customer_id`; non-superuser is rejected; token grants access scoped to the target customer; token carries the superuser's real `user_id`; expired token is rejected; a superuser token with no impersonation session still gets empty/not-found per Group 1's fix
- [ ] 3.5 Run users-service test suite and flake8 (`--max-line-length=100`) clean; PR merged

## 4. Centralized privileged-access audit hook — depends on 3

- [ ] 4.1 Add `privileged_access_logs` model + migration to each service (budget, users, ai, chat), modeled on `services/ai/app/models/audit_log.py::AIAuditLog`'s append-only shape, but generic (actor, target `customer_id`, request path, method, timestamp) rather than AI-specific
- [ ] 4.2 Add the audit-write hook at (or immediately after) `shared/security/dependencies.py:62`'s `get_validated_user`, firing whenever the decoded token carries the impersonation flag — each service writes to its own local table
- [ ] 4.3 Decide and implement the fail-closed/fail-open question for audit-write failures (design.md Open Questions) — writes should fail closed at minimum; confirm and implement the read-path behavior during this ticket
- [ ] 4.4 Tests per service: a read during impersonation produces a log entry; a write during impersonation produces a log entry; a normal (non-impersonation) request produces no entry; audit-write failure behavior matches the decision made in 4.3
- [ ] 4.5 Run full test suite (all services touched) and flake8 (`--max-line-length=100`) clean; PR merged

## 5. Impersonation UI: top bar picker + warning banner — depends on 3

- [ ] 5.1 Add `is_superuser` (and any impersonation-active state) to the decoded JWT claims surfaced by `AuthContext` (`frontend-typescript/src/context/AuthContext.tsx`)
- [ ] 5.2 Add a customer-search endpoint call (reuse the existing customer search pattern from `ManageGrantees.tsx`'s donor→grantee NGO search) wired to a new `<ImpersonatePicker />` component, rendered in `TopBar.tsx` to the left of the existing user menu, visible only when `isSuperuser` is true
- [ ] 5.3 Selecting a customer in the picker calls the impersonation-token endpoint (Group 3) and swaps the app's active auth token, without discarding the superuser's own original token client-side (needed for exit)
- [ ] 5.4 Add `<ImpersonationBanner />`, rendered once in `DashboardLayout` above `TopBar`, visible whenever an impersonation session is active, naming the impersonated customer, with an always-visible **Exit** control and no other way to hide it
- [ ] 5.5 Exit control ends the impersonation session and restores the superuser's own original session/token
- [ ] 5.6 Tests: picker is absent for non-superusers; banner appears immediately on impersonation start and persists across route changes; banner has no dismiss/hide control other than exit; exit restores the superuser's own session
- [ ] 5.7 Run frontend test suite and lint clean; PR merged

## 6. Disclosure — depends on 3, 4, 5

- [ ] 6.1 Add a subsection to `docs/legal/privacy-policy-stub.md` disclosing that superusers may temporarily access any organization's account (read and write) for support/demo/security/compliance purposes, and that every such action is logged
- [ ] 6.2 Add an "Administrative Access" section to `SECURITY.md` describing impersonation and the audit log as the mitigation
- [ ] 6.3 Check `docs/security/subprocessors.md` for whether any cross-reference is needed (expected: no change)
- [ ] 6.4 PR merged
