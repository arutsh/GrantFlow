## Why

Donors (funders) currently have no way to see, in one place, what they've funded: how many budgets they're backing, how much they've allocated in total, which grantees (NGOs) they support, and which budgets belong to which grantee. The existing `/dashboard` page is a single generic, owner-only view with hardcoded mock stats, and the budget list API only ever filters by `owner_id` (the grantee) — there is no code path today that lets a donor query budgets by `funding_customer_id`. This change adds a minimal, donor-facing dashboard: total budgets funded, total amount allocated, a grantee directory, and a funded-budgets list with a (deliberately mocked) "View Reports" action, since the report-review feature itself is tracked separately in `budget-reports` and isn't built yet.

A customer's `is_ngo` and `is_donor` flags (`CustomerModel`) are independent — the same customer can be both, e.g. an NGO that re-grants to its own sub-grantees. There is intentionally no separate `Grantee` model: whether a customer is acting as grantee or donor is determined per-budget (`owner_id` vs. `funding_customer_id`), not by a fixed type on the customer. The dashboard must therefore be driven by these flags rather than assume a customer is exclusively one role.

## What Changes

- Add `Budget.total_amount`, a denormalized running total of that budget's lines, recalculated whenever a budget line is created, updated, or deleted (avoids summing `budget_lines` via join on every dashboard read).
- Add donor-scoped backend read endpoints in `services/budget` (all gated to customers with `is_donor=True`):
  - Funded-budgets summary: total count + total allocated for the authenticated donor.
  - Grantee directory: distinct grantees the donor funds, enriched with name/country and a per-grantee budget count and allocated total.
  - Funded-budgets list: budgets where `funding_customer_id` matches the authenticated donor, enriched with grantee name (reusing the existing `populate_budget_with_user_details` enrichment pattern).
- Add a new frontend route/page (`/donor-dashboard`) with three stat tiles (Total Budgets, Total Allocated, Total Grantees), a grantee list, and a funded-budgets table whose "View Reports" button is rendered disabled with a "Coming soon" tooltip (no reporting UI exists yet — mocked on purpose).
- Extend the login/refresh response (`TokenResponse`) with `is_ngo`/`is_donor`, populated from the authenticating user's `CustomerModel`, and store them in `AuthContext`. The nav entry and the donor dashboard's content are shown based on `is_donor`; a customer with both `is_ngo` and `is_donor` sees both this dashboard and the existing owner-scoped one.

## Capabilities

### New Capabilities
- `donor-dashboard`: donor-facing summary stats (budget count, total allocated), grantee directory, and funded-budgets list with a mocked report-view action, scoped to the authenticated donor customer.

### Modified Capabilities
- None (`openspec/specs/` has no archived `budgets` capability yet to delta against — the `Budget.total_amount` field and funder-scoped query support are captured as part of the new `donor-dashboard` capability's backing requirements).

## Impact

- **New code**: `services/budget/app/api` donor-dashboard routes, corresponding CRUD/service functions, new Pydantic response schemas in `shared/schemas/`; `frontend-typescript/src/pages/DonorDashboard/` page + components; new `donorDashboardApi.ts`.
- **Modified code**: `services/budget/app/models/budget.py` (`total_amount` column), `app/crud/budget_crud.py` (`funding_customer_id` filter), `app/services/budget_line_services.py` (recalculate `total_amount` on line write), `shared/schemas/auth_schema.py` (`TokenResponse` gains `is_ngo`/`is_donor`), `services/users/app/api/auth_routes.py` (populate them on login/refresh), `frontend-typescript/src/context/AuthContext.tsx`, `App.tsx` routing, sidebar/nav component.
- **Database**: one new Alembic migration adding `budgets.total_amount` (nullable float, default 0), backfilled from existing `budget_lines.amount` sums for pre-existing rows.
- **Out of scope / explicit fast-follows**: real "View Reports" behavior (depends on the separate `budget-reports` change), pagination on the new list endpoints (acceptable for expected donor-scale data volumes today).
