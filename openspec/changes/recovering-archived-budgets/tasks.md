One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Backend restore endpoint

- [ ] 1.1 Add `POST /budgets/{id}/restore` route in `services/budget/main.py` (or the budget router module), owner-or-superuser authorized, matching the existing `_resolve_updatable_budget` owner path (no funder branch).
- [ ] 1.2 Add `restore_budget_service` in `services/budget/app/services/budget_services.py`: reject if `valid_budget.status != BudgetStatus.archived`; compute target status server-side — `confirmed` if `confirmed_at` is set and `start_date` is set, else `draft`; persist via `update_budget` in `services/budget/app/crud/budget_crud.py`, leaving `confirmed_at`/`start_date` untouched.
- [ ] 1.3 Add tests in `services/budget/tests/` covering: restore from archived-was-confirmed → `confirmed`; restore from archived-was-draft/ai_draft → `draft`; restore falls back to `draft` when `confirmed_at` is set but `start_date` is missing; restore rejected on a non-archived budget; restore rejected for a non-owner, non-superuser caller.
- [ ] 1.4 Run budget service tests and flake8 (max-line-length=100) clean; PR merged.

## 2. Frontend restore action — depends on 1

- [ ] 2.1 Add `restoreBudget(id)` in `frontend-typescript/src/api/budgetApi.ts` calling `POST /budgets/{id}/restore`.
- [ ] 2.2 In the budget card component(s) under `frontend-typescript/src/pages/Budgets/`, render a "Restore" action in place of Edit/Delete when `status === "archived"` and the current user owns the budget; wire it to `restoreBudget` with a React Query mutation that updates the cached budget on success and surfaces an error message on failure.
- [ ] 2.3 Verify manually against the local dev budget service: archive a confirmed budget, restore it, confirm it lands back on `confirmed` with `start_date` intact; archive a draft budget, restore it, confirm it lands on `draft`.
- [ ] 2.4 Run frontend lint/tests clean; PR merged.
