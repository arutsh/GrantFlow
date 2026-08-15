## Context

This change was originally scoped as parameter-driven cross-tenant reads (superuser passes an explicit `customer_id` per endpoint, extending the existing donor-grantee pattern — `services/users/app/services/donor_grantees_services.py:33-53`). That approach was discussed and superseded: the actual driving need is broader — logging into any customer's account (read *and* write, e.g. configuring BYOK AI settings during sales demos) without asking for their credentials or touching the DB directly. Rebuilding a parameter-driven override for every page one endpoint at a time doesn't scale to that; a session-level impersonation mechanism does, because it reuses the entire existing app unmodified.

Three implementation findings shaped the design:
- `services/budget/app/services/budget_services.py` (`list_budget_service`, `get_budget_service`, `_resolve_updatable_budget`, `_can_view_budget`/`get_viewable_budget_service`), `budget_line_services.py`, and `report_services.py` all contain unconditional `if valid_user["role"] == "superuser": <return everything unscoped>` branches, predating this change. This is a live gap independent of anything being built here: any superuser token can list every customer's budgets today, with no auditing and no concept of "which customer." Once impersonation exists, leaving this in place creates a redundant, unaudited backdoor next to the audited front door — worse than the gap alone.
- `services/ai/app/api/settings_routes.py:64-126` (AI provider key/model config) already gates on `role in {"superuser", "admin"}`, but every operation (`get_ai_settings`/`save_ai_settings`/`clear_ai_key`) is keyed by the caller's own `user_id` via `services/ai/app/crud/user_provider_key.py`'s `get_key`/`upsert_key`/`delete_key` — despite a frontend comment (`AiIntegrationsSection.tsx:209-210`) asserting it's customer-scoped. This is a pre-existing bug (two admins of the same org can silently create separate key rows, and an impersonating superuser using their own identity would create yet another one invisible to the org's real admins) that needs fixing for impersonation to behave correctly.
- The deployment is genuinely DB-per-service (verified via `docker-compose.local.yml`): one Postgres server, but each service connects to its own named database. No cross-service SQL joins are possible — carried over from the earlier version of this design and still true.

## Goals / Non-Goals

**Goals:**
- Let a superuser act as any customer — read and write, across any current or future page — without that customer's credentials and without direct DB access.
- Preserve true-actor accountability: every action taken during an impersonated session must be attributable to the real superuser, not the customer whose account is being used. This is a GDPR Art. 5(2) accountability / ISO 27001 A.8.15 logging requirement, not just a nice-to-have.
- Log every request made under impersonation — including reads ("even viewed") — not just mutations.
- Fix `UserProviderKey` to be genuinely customer-scoped.
- Disclose the capability in the privacy policy and security docs.

**Non-Goals:**
- Extending the previous parameter-driven `customer_id`-override pattern to budget/report/other endpoints. Superseded by impersonation — not needed.
- Modifying the existing donor-grantee superuser bypass. Left as-is; a separate, already-shipped mechanism, out of scope here.
- A cross-service audit *query* API or a full internal admin console (customer list/search beyond the top-bar picker, session history view, etc.). The audit table stays DB-only for v1; the UI is limited to starting/ending impersonation, not browsing the audit log.
- An ELT/data-warehouse layer for cross-service audit aggregation. Same reasoning as before — not warranted at this scale.
- Cross-tenant access to org profile/notifications/billing settings pages — these have no backend yet (frontend placeholders only in `frontend-typescript/src/pages/Settings/components/`); impersonation will cover them automatically once they're built, no extra work needed then.

## Decisions

### 1. Session-level impersonation, not parameter-driven access
Superuser mints a short-lived token scoped to a target `customer_id`, rather than passing an explicit `customer_id` per request. This is the reversal of the earlier version of this change's Decision 1 — see Context for why. The core tradeoff we accepted then (parameter-driven is cheaper but relies on every new endpoint remembering to scope) is exactly what impersonation avoids structurally: since the token just looks like a normal customer session, every existing and future endpoint already handles it correctly with zero new code.

### 2. Token carries the superuser's real identity, not a borrowed one
The impersonation token sets `customer_id = target`, admin-equivalent permissions, but `user_id = the superuser's own real id`.

**Alternative considered**: borrow the target customer's actual admin user's identity (so `user_id` in the token is theirs), which would make user-keyed features like the current `UserProviderKey` behave correctly without a data-model fix, and would make the customer's own later view of Settings show the change as if they made it. Rejected: this makes every `created_by`/`updated_by` field in the app misattribute the superuser's actions to a real named person who didn't perform them, which fails the accountability goal above and is exactly the kind of surface a GDPR/ISO audit would flag — "who actually did this" must be answerable without reconstructing it from session-boundary timestamps (which breaks under overlapping sessions, session leaks, etc.). Fixing `UserProviderKey` to be customer-scoped (Decision 4) removes the only reason to prefer identity-borrowing.

This also sidesteps a question that doesn't need answering: which admin to impersonate if a customer has several, or none yet (e.g. a fresh signup mid-onboarding). Since no identity is borrowed, it doesn't matter.

### 3. Centralized audit hook, not per-route instrumentation
Log every request under an impersonation-flagged token from a single point — the shared `get_validated_user` dependency (`shared/security/dependencies.py:62`), used by every service on every authenticated request — rather than requiring each route to call an audit helper.

**Alternative considered**: per-route audit calls (the approach in the earlier version of this change). Rejected for this mechanism specifically because the goal is "even viewed" — full coverage of reads, not just mutations — and per-route instrumentation can only cover routes someone remembered to instrument. A centralized hook can't be forgotten because it isn't opt-in.

**Granularity tradeoff, left open**: the centralized hook naturally logs at the request level (method + path + target `customer_id` + actor + timestamp), not with the fine-grained `resource_type`/`resource_id` the earlier per-route design could capture. Acceptable for v1 — coarse-but-complete beats fine-but-optional for an audit requirement — and specific high-value routes can be enriched later without weakening the baseline.

### 4. Fix `UserProviderKey` to be customer_id-keyed
Change the lookup key for AI provider settings from `user_id` to `customer_id`, matching the frontend's existing (currently false) assumption. This is a correctness fix independent of impersonation, but is required for impersonated AI-settings changes to be visible to the customer afterward, and closes the two-admins-shadow-each-other bug as a side effect.

### 5. Audit log stays per-service, not centralized
Same reasoning as the earlier version of this design: genuine DB-per-service isolation means a centralized table would add a synchronous cross-service dependency to every request under impersonation, which is worse here than in the earlier design since impersonated sessions can touch every service, not just budget. Each service logs locally.

### 6. Persistent, non-dismissible warning banner while impersonating
The picker lives in the top bar next to the existing user menu (`frontend-typescript/src/pages/Dashboard/TopBar.tsx`), visible only to superusers. Once a session is active, a banner naming the impersonated customer is shown on every page, with no way to hide it short of ending the session.

**Rationale**: this is a well-known failure mode in "log in as" tooling generally (Django's hijack, Stripe/Intercom-style impersonation) — an admin forgets they're impersonating and acts on a customer's live account thinking it's their own, or a customer's real data gets edited without anyone noticing the session was privileged. A dismissible banner (or none at all) doesn't prevent this; a persistent one does, cheaply — it's a single conditional wrapper around the layout, not per-page work.

### 7. Remove role-based bypasses in favor of customer_id-presence scoping
Delete the `if valid_user["role"] == "superuser": <unscoped>` branches in budget/report service functions rather than adding an impersonation-awareness check alongside them. Replace with: always scope by `valid_user.get("customer_id")`, exactly as already happens for a regular customer user; if it's absent (a superuser with no active impersonation session), the caller gets nothing — empty list, not-found for single-resource lookups.

**Why not keep the role check and just add "unless impersonating"**: that would leave two ways to reach cross-tenant data — impersonation, and a still-live role-based special case — which reintroduces the exact "unaudited backdoor next to the audited front door" problem this fix exists to close. Removing the branch entirely means `customer_id` presence is the only signal any of this code needs to understand, and it requires zero further changes to budget/report code when impersonation ships later: an impersonation token naturally carries `customer_id = target` (Decision 2), so the already-correct customer-scoped path starts working for impersonating superusers automatically, with no new code path added.

## Risks / Trade-offs

- **[Risk]** An impersonation token that leaks or outlives its intended use grants full read/write access to a customer's account. → **Mitigation**: short expiry (exact TTL is an implementation choice, not a spec-level decision), and every request under it is logged, so misuse is at least detectable even if not prevented in real time.
- **[Risk]** Centralized request-level audit logging is coarse — it won't by itself say "the superuser viewed budget #123," only "GET /budgets/123." → **Mitigation**: accepted for v1 (Decision 3); path alone is usually enough to reconstruct intent, and can be enriched later.
- **[Trade-off]** Logging every read, not just writes, means more audit volume and a stronger reliability bar (see Open Questions on fail-closed for reads). Accepted because impersonation sessions are inherently rare and short (support/demo use, not routine traffic), so volume stays low regardless.

## Migration Plan

1. Ship the `UserProviderKey` customer_id-keying fix first, independent of impersonation — it's a self-contained correctness fix with its own migration and doesn't depend on anything else in this change.
2. Ship the per-service `privileged_access_logs` tables and the centralized audit hook together with impersonation token issuance in the same window — an impersonation mechanism without audit logging from day one would be a real gap, not just a sequencing nicety, given the accountability goal.
3. No rollback complexity beyond standard migration reversibility.

## Open Questions

- **Fail-closed on reads vs. writes**: should a failed audit-log write block the request even for a plain page view, or only for mutations? Fail-closed on writes is the easier call (matches the earlier version of this change's reasoning); fail-closed on reads has a real UX cost (a broken audit table would lock a superuser out of *viewing* anything during an active demo). Left open — revisit during implementation.
- Exact impersonation token TTL.
- Should specific high-value routes (e.g. AI settings writes) get enriched `resource_type` logging in addition to the centralized coarse hook, or is coarse logging acceptable indefinitely?
