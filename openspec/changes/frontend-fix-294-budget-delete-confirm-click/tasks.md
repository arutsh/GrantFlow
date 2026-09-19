# Tasks

Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Fix delete confirmation click in BudgetListPage

- [ ] 1.1 Update `BudgetListPage.deleteBudget()` in `frontend-typescript/e2e/pages/BudgetListPage.ts` to click the "Yes" confirmation button (scoped to the same row) after clicking "Delete budget", and verify by reading the updated method against `ConfirmDeleteButton`'s rendered Yes/No markup
- [ ] 1.2 Run `frontend-typescript/e2e/specs/browser/auth-budget-crud.spec.ts` against the local docker-compose e2e stack and verify the delete-budget assertion (`toHaveCount(0)`) passes
- [ ] 1.3 Run the full e2e suite (`api` + `browser` projects) locally or via the `E2E Tests` CI workflow, confirm no regressions; PR merged
