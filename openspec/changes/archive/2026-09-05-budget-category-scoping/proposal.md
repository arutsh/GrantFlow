## Why

`BudgetCategoryModel` has no owner scope at all — no `customer_id`, no `budget_id`. Category reuse is a global lookup by name across the whole platform: `get_or_create_category_service`/`get_or_create_categories_by_names_service` match on `name` alone, so two unrelated budgets (even from different customers) that both end up with a category named "Travel" already share the exact same row today. The default category "Miscellaneous" is very likely one row shared across most budgets on the platform. This is why category rename/delete were never exposed via an API route despite existing in CRUD — shipping them as-is would let one customer's edit silently relabel another customer's budget. Fixing this requires giving categories a real owner before an edit feature can be safe.

## What Changes

- Add `budget_id` to `BudgetCategoryModel`; every category is owned by exactly one budget, never shared across budgets or customers.
- Re-scope category get-or-create/lookup logic from global-by-name to `(budget_id, name)` — still dedupes repeated names within one budget/import, never across budgets.
- Migrate existing data: categories referenced by exactly one budget get that `budget_id` directly; categories referenced by multiple budgets (real entanglement) get forked into per-budget copies with lines repointed; orphaned categories with no referencing lines are deleted.
- Drop the vestigial `donor_template_id` column/relationship from `BudgetCategoryModel` (dead in practice — no real code path sets it).
- Remove the unused `/donor-mapping/categories` POST/GET routes (incompatible with mandatory `budget_id`, unused by the frontend).
- Add `PATCH`/`DELETE /budget-categories/{id}` and `GET /budget-categories/by-budget/{id}`, each enforcing budget ownership (via the existing `get_budget(db, budget_id, customer_id)` pattern) and the existing confirmed-budget edit lock.
- Fix `update_budget_category` to set `updated_by` on edit (currently never populated, unlike `create_budget_category`) — done by hand for this file only, ahead of and independent from the separate, not-yet-implemented `audit-mixin-auto-population` change.
- **BREAKING**: `BudgetCategory` API schema drops `donor_template_id`, gains required `budget_id`.

## Capabilities

### New Capabilities
- `budget-categories`: category ownership (one budget per category, no cross-budget/cross-customer sharing), CRUD including edit/delete, and the get-or-create dedup behavior scoped per budget.

### Modified Capabilities
(none — no existing spec covers category ownership/CRUD today)

## Impact

- **Schema**: new migration on `services/budget` (`budget_categories` gains `budget_id` NOT NULL FK + unique `(budget_id, name)`, loses `donor_template_id`).
- **Backend**: `services/budget/app/models/budget.py`, `app/crud/budget_category_crud.py`, `app/services/budget_category_services.py`, `app/api/mapping_routes.py` (routes removed), new `app/api/budget_category_routes.py`, call-site updates in `budget_line_services.py` and `budget_services.py`.
- **Shared schema**: `shared/schemas/budget_line_schema.py` (`BudgetCategoryBase`/new `BudgetCategoryUpdate`).
- **Tests**: new unmocked coverage for the real dedup/ownership/lock behavior (currently zero — every existing test mocks the category service out).
- **Frontend**: `BudgetCategory` type update only in this change; an inline-rename UI is explicitly deferred to a follow-up.
