# Tasks

Workflow rule: one task group = one GitHub sub-issue (of this change's parent issue) = one PR, merged before the next group starts.

## 1. Fix budget deletion cascade for orphaned categories

- [ ] 1.1 Add `passive_deletes=True` to `BudgetModel.categories` in `services/budget/app/models/budget.py`
- [ ] 1.2 Add/extend a `services/budget` test that creates a budget, adds a line (auto-creating a category), deletes the line, then deletes the budget, and verify `DELETE /budgets/{id}` returns 200 with `success: true` instead of a 400
- [ ] 1.3 Run `frontend-typescript/e2e/specs/api/auth-budget-chain.spec.ts` against the local docker-compose e2e stack (or the `E2E Tests` CI workflow) and verify the DELETE-budget assertion passes
- [ ] 1.4 Run `services/budget`'s test suite and lint clean; PR merged
