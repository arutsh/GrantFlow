One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Data layer: migration, model, CRUD, service scoping (Budget)

- [x] 1.1 Write migration `services/budget/migrations/versions/000014_scope_budget_categories_to_budget.py` (`down_revision = "000013"`): add nullable `budget_id`; backfill single-referencing-budget rows directly; fork rows referenced by multiple budgets and repoint their `budget_lines.category_id`; delete zero-reference orphan rows (log all three counts); alter `budget_id` to `NOT NULL`; add FK (`ondelete="CASCADE"`) + index; add `UniqueConstraint(budget_id, name)`; drop `donor_template_id` column/FK. Write `downgrade()` as a schema-shape rollback only.
- [x] 1.2 Update `services/budget/app/models/budget.py`: `BudgetCategoryModel` gets `budget_id` FK + `budget` relationship, drops `donor_template_id`/`donor_template`; `BudgetModel` gets a `categories` back-populated relationship.
- [x] 1.3 Update `services/budget/app/models/mapping.py`: remove `DonorTemplateModel.categories` relationship (its counterpart FK is gone).
- [x] 1.4 Re-scope `services/budget/app/crud/budget_category_crud.py`: `create_budget_category`, `bulk_create_budget_categories`, `get_budget_category_by_name` (renamed from `get_budget_category_by_name_and_template_id`), `get_budget_categories_by_names` (renamed from `..._and_template_id`), and `list_budget_categories` all take `budget_id` instead of `donor_template_id`. Fix `update_budget_category` to accept `user_id` and set `existing_category.updated_by = user_id` before commit.
- [x] 1.5 Re-scope `services/budget/app/services/budget_category_services.py`: `get_or_create_category_service` and `get_or_create_categories_by_names_service` take a required `budget_id`; when `category_id` is given, verify `category.budget_id == budget_id` and reject otherwise. Add `update_budget_category_service`/`delete_budget_category_service` enforcing budget ownership (via `get_budget(db, category.budget_id, valid_user.get("customer_id"))`) and the confirmed-budget edit lock (reuse `_assert_budget_editable`/`is_budget_locked`).
- [x] 1.6 Update call sites to thread `budget_id` through: `services/budget/app/services/budget_line_services.py` (`create_budget_line_service`) and `services/budget/app/services/budget_services.py` (`create_budget_with_lines_service`).
- [x] 1.7 Update `services/budget/tests/factories/budget.py`: `BudgetCategoryFactory` gets `budget_id`, drops `donor_template_id`.
- [x] 1.8 Add unmocked coverage: CRUD/service-level tests proving name lookup is scoped to `budget_id` (same name in two budgets → two rows, same name twice in one budget → one row), and new tests for `update_budget_category_service`/`delete_budget_category_service` covering ownership rejection, lock rejection, and `updated_by` actually changing on edit.
- [ ] 1.9 Run `services/budget` test suite clean; PR merged (`Closes #<ticket>`).

## 2. API surface: routes and shared schema (Budget) — depends on 1

- [ ] 2.1 Update `shared/schemas/budget_line_schema.py`: `BudgetCategoryBase` drops `donor_template_id`, gains required `budget_id`; add `BudgetCategoryUpdate` (`name`/`code`, both optional).
- [ ] 2.2 Remove the `POST /donor-mapping/categories` and `GET /donor-mapping/categories` (+ `/categories/{template_id}`) endpoints from `services/budget/app/api/mapping_routes.py`.
- [ ] 2.3 Add `services/budget/app/api/budget_category_routes.py` (`prefix="/budget-categories"`, matching `budget_line_routes.py`'s flat-router convention): `GET /budget-categories/by-budget/{budget_id}`, `PATCH /budget-categories/{category_id}`, `DELETE /budget-categories/{category_id}`.
- [ ] 2.4 Register the new router in `services/budget/main.py` alongside the existing `budget_line_routes` registration.
- [ ] 2.5 Add `services/budget/tests/test_budget_category_routes.py` mirroring `budget_line_routes`' test shape (ownership rejection, lock rejection, happy-path edit/delete/list).
- [ ] 2.6 Run `services/budget` test suite clean; PR merged (`Closes #<ticket>`).

## 3. Frontend type sync (Frontend) — depends on 2

- [ ] 3.1 Update `frontend-typescript/src/pages/Budgets/types/budget.ts`: `BudgetCategory` type drops `donor_template_id`, gains `budget_id`.
- [ ] 3.2 Confirm `SingleBudgetViewContext.tsx`'s `budgetCategories`/`budgetCategoryNames` derivation and `AddBudgetLine.tsx`'s dropdown still compile and behave correctly against the updated type (no inline-rename UI in this ticket — that's a separate follow-up).
- [ ] 3.3 Run frontend typecheck/build clean; PR merged (`Closes #<ticket>`).
