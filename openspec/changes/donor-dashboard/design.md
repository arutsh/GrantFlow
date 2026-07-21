## Context

`services/budget` today models only the grantee side of a `Budget`: `BudgetModel.owner_id` is the NGO, `funding_customer_id`/`external_funder_name` identify the donor, but `list_budgets` (`app/crud/budget_crud.py`) filters exclusively on `owner_id`, and `list_budget_service` (`app/services/budget_services.py`) resolves the current user's own budgets the same way — there is no code path that queries by `funding_customer_id`. There is also no aggregate/total field on `Budget`; the only amount lives on `BudgetLineModel.amount`. Donor vs. grantee is not a `UserRole` (`superuser | admin | user`) — it's two independent booleans on `CustomerModel` (`is_ngo`, `is_donor`), checked ad hoc via `services/budget/app/services/customer_client.py` (`validate_customer_can_fund`, `validate_customer_can_own`), which calls the users service over HTTP (`get_customer_cached`). The JWT payload produced by `get_validated_user` carries `customer_id`/`role`/`token`, not `is_donor`.

There is already a working cross-service enrichment pattern worth reusing rather than reinventing: `populate_budget_with_user_details` (`app/services/budget_services.py:207`) collects `owner_id`/`funding_customer_id` values off a batch of budgets, calls `get_customers_by_ids` once (batched, not N+1), and merges customer name/country back onto each budget as `owner`/`funder`. The frontend (`frontend-typescript`, React 19 + Vite + React Router v7 + TanStack Query/Table + Tailwind v4, custom UI kit under `src/components/ui/`) has one existing dashboard (`src/pages/Dashboard/Dashboard.tsx`) with hardcoded mock stats and no donor-specific page. `AuthContext` only holds `username`/`token` today — no `customer_id` or `is_donor` is available client-side.

Critically, `is_ngo` and `is_donor` are independent booleans on the same `CustomerModel` row — a customer can be both at once (e.g. an NGO that re-grants funds to its own sub-grantees). This is why there is no separate `Grantee` model: `owner_id` and `funding_customer_id` both just point at `customers.id`, and which "hat" a given customer is wearing is entirely determined by which column of which budget references them, not by its type. The dashboard's job is to read both flags on the logged-in customer and decide what to show — not to assume a customer is exclusively one or the other.

## Goals / Non-Goals

**Goals:**
- Let a donor see, without joining data by hand: how many budgets they fund, how much they've allocated in total, who their grantees are, and a list of those budgets.
- Compute the allocated total cheaply (no per-request join across `budget_lines`) so the dashboard stays fast as data grows.
- Reuse the codebase's existing batched-enrichment and donor/grantee-validation conventions instead of introducing new ones.

**Non-Goals:**
- Real "View Reports" behavior — depends on the separate `budget-reports` change; this change only renders a disabled button + tooltip.
- A general-purpose role/permission system — this change only needs `is_ngo`/`is_donor` to reach the client; it doesn't add a `UserRole` value or restructure auth.
- Pagination/cursor support on the new list endpoints — acceptable given expected donor-scale data volumes (a handful to low hundreds of budgets); flagged as a follow-up if that assumption breaks.
- Overspend/variance logic ("On Track" / "Over Budget") — the existing generic `/dashboard` mock stats already imply this; it's a separate, larger feature and not part of this change.

## Decisions

**Denormalize `Budget.total_amount`, recalculated on budget-line writes — not summed via join at read time.**
The user explicitly asked to avoid join-based aggregation for the dashboard. Adding `total_amount: float` (default 0) to `BudgetModel` and recomputing it (`sum(line.amount for line in budget.lines)`) inside the existing budget-line create/update/delete service functions (`app/services/budget_line_services.py`) keeps every dashboard read a plain column read/SUM, at the cost of a few extra lines in the line-mutation path. Alternative considered: DB trigger — rejected as inconsistent with the rest of the service, which does all business logic in Python/SQLAlchemy, not SQL triggers. A more sophisticated caching/event-driven recalculation strategy was mentioned as a possible future direction but is explicitly out of scope here; this change only needs the recalculation to be correct, not maximally efficient.

**New donor-scoped endpoints live under `/budgets/funded/*`, a distinct sub-resource from the existing owner-scoped `/budgets/`.**
Mirrors a common REST convention for "the current actor's other relationship to this resource" (e.g. GitHub's `/user/repos` vs. `/orgs/{org}/repos`) rather than overloading `GET /budgets/` with a query param that silently flips its filter semantics between owner and funder. Three routes:
- `GET /budgets/funded/summary` → `{ "total_budgets": int, "total_allocated": float }`, one `COUNT`/`SUM(total_amount)` query filtered by `funding_customer_id`.
- `GET /budgets/funded/grantees` → one row per distinct `owner_id` funded by this donor, `GROUP BY owner_id` for `budgets_count`/`SUM(total_amount)`, then a single batched `get_customers_by_ids` call (same pattern as `populate_budget_with_user_details`) to attach grantee `name`/`country`.
- `GET /budgets/funded/` → budgets where `funding_customer_id == current customer`, reusing `list_budgets` (extended with a `funding_customer_id` filter param) and the existing `populate_budget_with_user_details` enrichment for the `owner` (grantee) name.
All three call a new `require_donor(valid_user)` guard (thin wrapper around the existing `get_customer_cached`/`is_donor` check already used by `validate_customer_can_fund`) and return 403 for non-donor customers.

**Expose `is_ngo`/`is_donor` to the frontend via the login/refresh response, and use them to decide what the dashboard shows.**
`TokenResponse` (`shared/schemas/auth_schema.py`) gains `is_ngo`/`is_donor` fields; `/auth/login` and `/auth/refresh` (`services/users/app/api/auth_routes.py`) look up the authenticating user's `CustomerModel` and populate them. `AuthContext` stores both flags alongside `token`/`username`. The new `/donor-dashboard` route and its nav entry render only when `isDonor` is true; a customer with both `is_ngo` and `is_donor` sees both the existing (owner-scoped) dashboard and this one — the two are additive, not alternatives, matching a customer's ability to hold both roles at once. This is a small, targeted extension of the existing login contract (two booleans), not a general role/permission system. Alternative considered: keep the dashboard reachable by any authenticated user and let the backend's 403 decide what's shown — rejected once the requirement became "decide what to display from the flags," since a 403-driven UI can't distinguish "not a donor" from "donor with zero data" without an extra round trip, and can't drive nav visibility at all.

**"View Reports" is a disabled button with a tooltip, not a fake modal.**
Per explicit product decision: showing fabricated report data risks being mistaken for real data; a disabled control with a "Coming soon" tooltip communicates the real state honestly and costs nothing to remove once `budget-reports` ships.

## Risks / Trade-offs

- **[Risk]** `total_amount` can drift from the true sum of `budget_lines` if a line is ever mutated through a path that bypasses `budget_line_services.py` (e.g. a future bulk-import script, direct SQL). → **Mitigation**: recalculation lives in the one place all line mutations currently go through; flagged in code comments/tasks so any new line-mutation path is obligated to update it too.
- **[Risk]** No pagination on `/budgets/funded/` or `/budgets/funded/grantees` means a donor funding a very large number of budgets gets one large response. → **Mitigation**: explicitly accepted for current expected scale; add `limit`/`offset` later without a breaking change if it becomes a problem (mirrors the existing hardcoded `limit=100` on `list_budgets`, which has the same shape of limitation today).
- **[Trade-off]** `is_ngo`/`is_donor` travel in the login/refresh JSON body (not just inside the signed JWT), so a client can read but not spoof them — the backend's `require_donor` 403 gate on the actual `/budgets/funded/*` endpoints stays authoritative regardless of what the nav shows or hides.

## Migration Plan

One new Alembic revision on `services/budget`, chained off the current head, adding `budgets.total_amount` (`Float`, nullable, `server_default '0'`), followed by a one-time backfill (`UPDATE budgets SET total_amount = (SELECT COALESCE(SUM(amount), 0) FROM budget_lines WHERE budget_lines.budget_id = budgets.id)`) so existing budgets show a correct total immediately rather than 0. Purely additive — rollback is `alembic downgrade -1`, dropping the column.

## Open Questions

- Whether `/budgets/funded/grantees` should also surface each grantee's budget `status` breakdown (e.g. how many are draft/active) — deferred; today's proposal keeps it to count + total allocated per the minimal "list of grantees" ask.
