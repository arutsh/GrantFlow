## Context

`CustomerModel` (`services/users/app/models/customer.py`) represents both donors and grantees via two booleans (`is_donor`, `is_ngo`) — a customer can be both. `BudgetModel` (`services/budget/app/models/budget.py`) has `owner_id` (grantee) and `funding_customer_id` (donor, nullable), both plain `GUID()` columns with no real FK, since users and budget are separate services with separate databases. Budget creation (`create_budget_service`) and update (`update_budget_service`, both in `services/budget/app/services/budget_services.py`) currently only check `validate_customer_can_fund(funding_customer_id)` — that the customer *is* a donor at all, not that *this* donor has approved *this* grantee.

The user has already drafted a starting model, `DonorGranteeModel`, in `customer.py`: an audited table with `donor_id`/`grantee_id` FKs to `customers.id` and `@validates` hooks enforcing `donor.is_donor` / `grantee.is_ngo`. This design builds directly on it.

Two cross-service communication patterns already exist in this codebase and are relevant precedent:
1. **Synchronous HTTP, no service auth** — `services/budget/app/services/customer_client.py` (`requests` + `lru_cache`) and `services/budget/app/services/user_client.py` (`httpx.AsyncClient`, forwards the end user's JWT). Neither has any service-to-service auth (API key, internal JWT, mTLS) — this is a known, accepted gap in this codebase (see GitHub #137, tracked separately).
2. **Event-driven local cache** — `users` publishes `user.*` events over RabbitMQ; `budget` consumes them into a local `UserProfileModel` cache (`app/services/event_consumer.py`, `app/services/event_handlers.py`, `app/models/user_cache.py`).

## Goals / Non-Goals

**Goals:**
- A donor can register that they approve a specific grantee, and revoke it, with only the donor able to write these records.
- Budget creation and update reject any attempt to set `funding_customer_id` to a donor that hasn't approved the budget's owner.
- Revocation takes effect immediately for new budget-funding attempts (no caching that would mask a revoke).
- Follow existing codebase conventions (auth style, error conventions, client patterns) rather than introducing new ones.

**Non-Goals:**
- No invite/accept workflow — presence of a row is the approval, decided with the user; no `status` field, no grantee-side write access.
- No event-driven cache for this relationship in this change — synchronous HTTP now, matching the `customer_client.py` pattern. The event-driven cache pattern is proven in this codebase and is the natural next step if latency or users-service coupling becomes a real problem, but is out of scope here.
- No frontend work — covered by the separate `donor-grantee-relationship-frontend` change.
- No retroactive re-validation of existing budgets when a relationship is revoked — only new create/update attempts are gated.
- No service-to-service auth mechanism introduced — the new `exists` endpoint follows the existing no-auth "internal service endpoint" convention already used by `POST /customers/by_ids/`, rather than inventing auth that nothing else in the codebase has.

## Decisions

**1. Relationship ownership lives in the users service, not budget.** `donor_id`/`grantee_id` are both customer identities, and `CustomerModel` already lives in `users` with real FKs available there (unlike budget, which only ever holds bare UUIDs for cross-service refs). This matches how the user already wrote `DonorGranteeModel`.

**2. Presence-based approval, no status field.** Alternative considered: a `pending`/`approved`/`rejected` status enum supporting a donor-invites-then-grantee-accepts flow. Rejected for this change — the user decided donor-only, unilateral creation is sufficient for now, and it matches the model as drafted (no status column). If an accept step is wanted later, it's an additive column + endpoint, not a rework.

**3. Synchronous HTTP check, no cache, for the cross-service gate.** Alternative considered: extend the existing RabbitMQ event/cache pattern (`user.*` → `UserProfileModel`) with `donor_grantee.*` events into a new budget-side cache table. Rejected for now: this relationship changes rarely (donor approves once) and is checked only at the moment of setting `funding_customer_id`, so the added latency of one HTTP call is acceptable, and it avoids building a new event schema, publisher call site, consumer handler, and cache migration for what is currently low-value distributed-systems complexity. Explicitly **not** using `lru_cache` (unlike `get_customer_cached`) because revocation must take effect on the next attempt — this is a deliberate deviation from the sibling `customer_client.py`, called out so it isn't "fixed" into consistency later.

**4. `exists` endpoint is unauthenticated, matching `POST /customers/by_ids/`.** Alternative considered: require a service-level credential. Rejected — no such mechanism exists anywhere in this codebase today; inventing one for a single endpoint would be inconsistent and is a larger, separate concern (tracked as #137-adjacent debt, not fixed here).

**5. `donor_id`/`customer_id` are always derived from the caller's JWT claims, never accepted as parameters — except for a `superuser` caller, who must supply them explicitly, and who bypasses ownership scoping entirely.** This claim-derivation is the actual authorization boundary preventing one donor from acting on behalf of another: on `POST`, `donor_id` is taken from the JWT, not the body; on `GET` (list), the scoping `customer_id` is taken from the JWT, not a query param; on `DELETE`, the row's `donor_id` must match the caller. The superuser exception applies uniformly across all three: a superuser isn't attached to any donor/grantee customer of their own, so there's no claim to derive from — `POST`/`GET` require the equivalent identifier to be supplied explicitly (rejected with 400 if omitted) and act on it directly, while `DELETE` skips the ownership check altogether (a superuser may delete any record by `id`). This mirrors the existing `owner_id` override in `budget_services.create_budget_service`, except that override falls back to a placeholder value when omitted (flagged `# FIXME: Temp workaround`); this one rejects the request outright instead — a deliberate, permanent design choice, not a stopgap. Non-superuser behavior is unchanged throughout: any `donor_id`/`customer_id` a non-superuser submits is silently ignored in favor of their own claim.

**6. Both `create_budget_service` and `update_budget_service` are gated, not just create.** `update_budget_service` has its own independent `validate_customer_can_fund` call today; without gating it too, a grantee could create a funder-less budget then `PATCH` in a `funding_customer_id` and bypass the create-time gate entirely. The new check is placed after `owner_id`/`valid_budget.owner_id` is resolved in each function (including the superuser-override branch in create), since the check needs the *final* owner, not the request's raw input.

**7. No superuser bypass on the new check.** Matches the existing, unconditional behavior of `validate_customer_can_fund` (which superusers also can't skip), as opposed to `validate_customer_can_own`, which *is* skipped for superusers per an existing `# TODO revisit this` comment. Kept consistent with the check it sits beside rather than introducing a third bypass behavior.

## Risks / Trade-offs

- **[Risk] Budget creation/update now depends on users-service availability for any funded budget.** → Mitigation: this dependency already exists today via `validate_customer_can_fund`; this change adds one more call of the same shape, not a new failure mode.
- **[Risk] No service-to-service auth on the `exists` endpoint means anything that can reach the users service internally can query relationship existence.** → Mitigation: matches the existing, accepted posture of every other internal endpoint in this codebase (`by_ids` etc.); not a regression, and fixing it repo-wide is out of scope.
- **[Risk] `AuditMixin.id` default (`uuid.uuid4()`, a `UUID` object) differs from the model's current shadowing `id` default (`str(uuid.uuid4())`, a `str`).** Dropping the shadow column changes the concrete Python type produced at insert time. → Mitigation: `GUID.process_bind_param` (the custom type decorator) accepts both `UUID` and `str`, so this is safe; called out explicitly in the PR description as a deliberate, verified behavior change, not an oversight.
- **[Risk] Extending `GET /customers/` with filters and adding auth to previously-open endpoints, in a backend-only change ahead of the frontend change that will use them.** → Mitigation: adding auth to a previously-unauthenticated endpoint is strictly safer and has no consumers yet (nothing currently calls these routes through the gateway); shipping it here means the frontend change isn't blocked waiting on a backend follow-up.
- **[Trade-off] Duplicate-relationship conflict (`IntegrityError` on the unique constraint) returns `400`, not `409`.** The codebase has no existing `409` usage anywhere and `DomainError` defaults to `400`; consistency with existing conventions was weighted over strict HTTP-semantics correctness.

## Migration Plan

1. Ship the users-service migration (`000004_add_donor_grantees.py`) and model/route changes first; deploy users service.
2. Ship the budget-service client + gate changes; deploy budget service. Between step 1 and step 2 landing, budget's behavior is unchanged (old code doesn't call the new endpoint yet).
3. Ship gateway route additions (nginx/Caddy) — required before any external caller (including the future frontend change) can reach `/api/v1/donor-grantees/` or `/api/v1/customers/`; not required for the budget→users internal call, which bypasses the gateway.
4. No backfill needed — no existing data represents this relationship; all `donor_grantees` rows are created going forward by donors, starting from empty.
5. **Rollback**: revert the budget-service gate first (stops enforcement, budget creation returns to today's behavior) before rolling back the users-service migration, to avoid budget calling a removed endpoint.

## Open Questions

- Should `update_budget_service`'s gate apply to *every* edit that touches `funding_customer_id`, including the funder-confirm path (`is_funder_confirm` in `_resolve_updatable_budget`)? Current plan: yes, uniformly, since `is_funder_confirm` still requires `funding_customer_id` to already be set and matching the caller — the relationship would already have been validated when it was first set. Worth a second look during implementation if that path behaves unexpectedly.
- Confirm whether extending `list_customers` filters and adding auth to `customer_routes.py` should ship in this change or be deferred to the frontend change, since nothing in this backend change actually calls the filtered endpoint. Current plan keeps it here so the frontend change isn't blocked, but it could move if that coupling feels wrong.
