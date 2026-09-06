## Context

`BudgetCategoryModel` (`services/budget/app/models/budget.py`) has one FK today, `donor_template_id`, and it's vestigial: every real category-creation path (`create_budget_line_service`, `create_budget_with_lines_service`) calls `get_or_create_category_service`/`get_or_create_categories_by_names_service` with `donor_template_id` always `None`. Those functions dedupe purely by `name`, globally, across every customer and budget on the platform. `update_budget_category`/`delete_budget_category` exist in `budget_category_crud.py` but were never wired to a route — consistent with someone stopping short of shipping a rename that could silently mutate another org's category label. No test exercises this real behavior; every existing test mocks the category service out entirely.

Scope was deliberately chosen as `budget_id`, not `customer_id`: even within one customer, two different budgets may want an identically-named category to mean different things, and budget-scoping avoids the open question of whether a rename should propagate to a customer's other budgets — there is no sibling relationship once each budget owns its category rows outright.

## Goals / Non-Goals

**Goals:**
- Every `BudgetCategoryModel` row is owned by exactly one budget; no row is ever shared across budgets.
- Category name dedup still works within a single budget/import (repeated "Travel" rows in one sheet share one row), but never across budgets.
- Make `update_budget_category`/`delete_budget_category` safe to expose via a real route, with ownership and confirmed-budget-lock enforcement.
- Fix `update_budget_category` never setting `updated_by` on edit.
- Migrate existing data to the new shape without silent data loss beyond already-dead orphan rows.

**Non-Goals:**
- Customer-level (cross-budget) category sharing/reuse — explicitly rejected in favor of budget-level ownership.
- The general `audit-mixin-auto-population` mechanism (ContextVar + SQLAlchemy event listener) — this change fixes `updated_by` by hand, only in `budget_category_crud.py`, matching the manual-assignment pattern already used elsewhere in that file. The same gap in `budget_crud.py`/`budget_line_crud.py` stays out of scope.
- Redesigning donor-template fingerprint matching (`DonorTemplateModel`, tracked separately in `budget-template-storing`) — this change only removes the dead `donor_template_id` FK from `BudgetCategoryModel`; it does not touch `DonorTemplateModel` itself.
- Frontend inline-rename UI — deferred to a follow-up once the backend lands; this change only updates the `BudgetCategory` TS type for schema compatibility.

## Decisions

**1. Migration backfill: hybrid resolution, not pure "leave nullable" or pure "fork everything."**
The target model requires `budget_id` to be `NOT NULL`, so leaving ambiguous rows null isn't viable. Forking every row regardless of whether it's actually shared is more churn than the data needs — most category rows are already referenced by exactly one budget in practice. Chosen approach, in the raw-SQL, explicit-row-count style of `000011_drop_dormant_mapping_tables.py`:
- Categories referenced by exactly one distinct `budget_id` (via `budget_lines.category_id`) get that `budget_id` directly — no forking.
- Categories referenced by more than one distinct `budget_id` (the real entanglement — e.g. "Miscellaneous") keep the original row on one referencing budget (`MIN(budget_id)` for determinism) and get a forked copy per additional referencing budget, with those budgets' lines repointed to the fork.
- Categories referenced by zero lines (orphans from the retired `/donor-mapping/categories` POST route) are deleted outright, with the deleted count logged for auditability.

**2. `ondelete="CASCADE"` on the new `budget_categories.budget_id` FK.**
No existing precedent to match — `budget_lines.budget_id`'s FK has no `ondelete` clause today (checked `641370375898_initial_migration.py`). Chosen anyway: once a category is exclusively owned by one budget, deleting that budget should take its categories with it: nothing else can reference them once `budget_id` is mandatory.

**3. Add `UniqueConstraint(budget_id, name)`.**
Not explicitly required by the proposal but a natural DB-level backstop for the new dedup key — prevents a future application-level bug from silently producing duplicate category rows within one budget the way the old global lookup silently produced duplicates across budgets.

**4. Drop `donor_template_id` from `BudgetCategoryModel` in this same change rather than leaving it.**
It's dead in practice, and leaving it next to a now-mandatory `budget_id` creates confusing dual-scoping with no working code path. If donor-template-linked category reuse is ever redesigned (tracked separately under `budget-template-storing`, itself unscoped/exploratory), it can be designed fresh rather than resurrecting this unused field.

**5. Remove `/donor-mapping/categories` POST/GET routes.**
Unused by the frontend, and the POST path has no way to supply a `budget_id`, so it cannot coexist with mandatory scoping — it would either break at request time or need to stay permanently disconnected from the new column.

**6. New routes are flat (`/budget-categories/{id}`), matching `budget_line_routes.py`'s convention, not nested under `/budgets/{budget_id}/...`.**
Ownership is enforced in the service layer via the existing `get_budget(db, budget_id, customer_id)` pattern already used by `budget_line_services.py`, not via URL nesting — consistent with how budget lines already work.

**7. No standalone `POST /budget-categories/`.**
Creation stays implicit via the line-create paths (`get_or_create_category_service`), matching today's behavior — there's no existing "create a category on its own" UI flow to preserve.

## Risks / Trade-offs

- **[Risk]** The multi-budget fork step in the migration is the one non-trivial data rewrite — if the "which budgets reference this category" query is wrong, lines could get repointed incorrectly. → **Mitigation**: scope the fork logic to a single, auditable SQL pass keyed on `budget_lines.category_id`/`budget_id`, log every fork and orphan-delete count, and manually verify against a seeded dataset covering all three cases (single-budget, multi-budget, orphan) before merging — no automated migration test suite exists in this repo to lean on instead.
- **[Risk]** `UniqueConstraint(budget_id, name)` could reject a legitimate re-import if application-level dedup logic and the DB constraint disagree on case-sensitivity or whitespace normalization. → **Mitigation**: `get_or_create_category_service`'s existing lookup must match the constraint's exact-match semantics; no normalization is introduced by this change, so behavior stays consistent with today's (equally exact-match) global lookup.
- **[Trade-off]** Removing `/donor-mapping/categories` is a public API surface removal, not purely additive (**BREAKING**, called out in the proposal). Accepted because it's unused by the frontend and incompatible with mandatory `budget_id`.
- **[Trade-off]** Frontend inline-rename UI is deferred — this change makes editing *safe* at the API level but doesn't yet expose it in the product. Accepted to keep this change bounded to the backend ownership fix.

## Migration Plan

1. Add nullable `budget_id` column to `budget_categories`.
2. Run the three-case backfill (single-budget direct assignment, multi-budget fork + line repoint, zero-reference delete), logging counts for each case.
3. Alter `budget_id` to `NOT NULL`, add the FK (`ondelete="CASCADE"`), index, and `UniqueConstraint(budget_id, name)`.
4. Drop `donor_template_id` column and its FK in the same migration.
5. `downgrade()` drops what `upgrade()` added (constraint, FK, index, columns) — a schema-shape rollback only, matching `000013`'s convention; it does not attempt to un-fork data or restore `donor_template_id` values.
6. Deploy order: migration must land before the model/CRUD/service/route code that assumes `budget_id` is present and mandatory — standard Alembic-then-app-code sequencing, no dual-write/expand-contract needed since there's no live-traffic window where old and new code must both work against the same schema (single-service deploy, brief downtime acceptable per existing deployment practice).

## Open Questions

None outstanding — orphan-row deletion, `donor_template_id` removal, and `/donor-mapping/categories` route removal were each explicitly confirmed during proposal discussion.
