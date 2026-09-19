# Proposal

## Why

`DELETE /api/v1/budgets/{id}` returns a 400 ("Budget cannot be deleted while it has existing reports, funding receipts, or currency conversions") for budgets that have none of those, whenever a budget line was ever created and later deleted on that budget. This blocks legitimate budget deletion and was caught by the `auth-budget-chain` e2e spec's DELETE-budget step in CI, but it is a real product bug, not a test bug — any grantee who adds then removes a line before deleting a draft budget hits it.

## What Changes

- `BudgetModel.categories` gets `passive_deletes=True` so SQLAlchemy's ORM defers to the database's existing `ON DELETE CASCADE` on `budget_categories.budget_id` instead of trying to lazy-load the collection and null out each child's non-nullable `budget_id` during flush (which raises the spurious `IntegrityError`).
- Out of scope: cleaning up an orphaned category when its last line is deleted is a separate, pre-existing bookkeeping gap (also related to the already-known global-category-namespace issue) and is not needed to fix this bug — `passive_deletes=True` makes budget deletion correct regardless of whether an orphaned category row exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — this restores compliance with the already-declared `async-persistence` requirement ("No lazy-load MissingGreenlet risk": every relationship a route/service reads SHALL be explicitly eager-loaded or never accessed outside an awaited context, and no request path SHALL trigger an implicit lazy-load) and the `budget-categories` requirement that every category belongs to exactly one budget without ever becoming a dangling reference; it does not change either requirement's text.

## Impact

- `services/budget/app/models/budget.py` (`BudgetModel.categories` relationship)
- Fixes `DELETE /api/v1/budgets/{id}` for any budget that ever had a line added and removed
- Unblocks `frontend-typescript/e2e/specs/api/auth-budget-chain.spec.ts` in the `E2E Tests` CI workflow
