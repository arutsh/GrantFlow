# Design

## Context

See proposal.md - Why for the failure mode. Relevant existing state:

- `budget_categories.budget_id` has a DB-level FK with `ondelete="CASCADE"` (`services/budget/migrations/versions/000014_scope_budget_categories_to_budget.py`), added deliberately when categories were scoped one-per-budget — the DB already expects categories to disappear when their budget does.
- `BudgetModel.categories` (`services/budget/app/models/budget.py`) is a plain `relationship(..., back_populates="budget")` with no `cascade` and no `passive_deletes` setting.
- `delete_budget_service` (`services/budget/app/services/budget_services.py`) calls `get_budget_service`, which does **not** eager-load `categories` in this path, then calls `session.delete(budget)` + `commit()`.
- Without `passive_deletes=True`, SQLAlchemy's unit-of-work treats "this budget is being deleted" as "I must disassociate its `categories` collection" — since there's no delete cascade configured, it lazy-loads the (unloaded) collection during flush and issues an `UPDATE budget_categories SET budget_id = NULL ...` for each row, which the DB rejects (`budget_id` is `nullable=False`), surfacing as `IntegrityError` → the generic 400.
- Because the collection load happens inside `flush()`, which the SQLAlchemy asyncio extension runs inside a greenlet, this doesn't crash as a `MissingGreenlet` — it produces a normal `IntegrityError`, so it slipped past the `async-persistence` capability's existing "no implicit lazy-load" guard without tripping any greenlet-specific detection.

## Goals / Non-Goals

**Goals:**
- Make `DELETE /api/v1/budgets/{id}` succeed for a budget whose only remaining "problem" is a category row (no lines, reports, receipts, or currency conversions).
- Keep the DB as the single source of truth for the cascade, rather than teaching the ORM to duplicate it.

**Non-Goals:**
- Cleaning up orphaned `budget_categories` rows when a line is deleted (separate, pre-existing bookkeeping gap; not required for this fix — see proposal.md).
- Changing cascade behavior for `budgets.lines` or `budgets.reports` — those intentionally block budget deletion via `IntegrityError` today (a budget with real lines/reports/receipts should not be silently hard-deletable), and that behavior is unaffected by this change.

## Decisions

**Use `passive_deletes=True` on `BudgetModel.categories`, not ORM-level `cascade="all, delete-orphan"`.**
- `passive_deletes=True` tells SQLAlchemy "don't manage this relationship's deletes yourself, the DB's `ON DELETE CASCADE` already does it" — it skips the lazy-load-and-null-out step entirely and just issues `DELETE FROM budgets WHERE id = ...`, letting Postgres cascade.
- Alternative considered: `cascade="all, delete-orphan"`. This would make SQLAlchemy load the collection and emit an explicit `DELETE FROM budget_categories WHERE id IN (...)` before deleting the budget — functionally similar end state, but it still requires the lazy-load (same eager-load discipline the `async-persistence` capability calls for) and does redundant work the DB already does via its own `ON DELETE CASCADE`. `passive_deletes=True` is the smaller, more precise fix that matches the existing DB-level intent from migration `000014`.
- `passive_deletes=True` requires the DB constraint to actually be `ON DELETE CASCADE` (true here, confirmed in the migration) — it would be the wrong choice if the constraint were `RESTRICT`/`NO ACTION`, since then rows would just silently fail to delete.

## Risks / Trade-offs

- [`passive_deletes=True` silently relies on the DB constraint matching model expectations; if a future migration changes `budget_categories_budget_id_fkey` back to `RESTRICT` without updating the model, budget deletion would start failing again with a real (unmasked) `IntegrityError`] → Acceptable: that failure mode is the same generic `IntegrityError` → 400 path already in place for lines/reports, so it fails safe (blocks deletion, doesn't corrupt data) rather than silently.
- [Orphaned categories with zero lines still accumulate until their budget is deleted] → Out of scope per Non-Goals; tracked separately as a known bookkeeping gap, not a correctness or security issue.
