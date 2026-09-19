# Proposal

## Why

The browser e2e spec (`auth-budget-crud.spec.ts`) fails in CI on its final assertion: after calling `BudgetListPage.deleteBudget()`, the budget row is expected to disappear but never does. The helper only clicks the delete icon once, which merely reveals a Yes/No confirmation — it never confirms, so no delete/archive ever happens and the test fails on a false negative unrelated to any product bug.

## What Changes

- `BudgetListPage.deleteBudget()` clicks the "Delete budget" icon button, then clicks the resulting "Yes" confirmation button, so the archive mutation actually fires before the test asserts the row is gone.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — this fixes the `e2e-testing` capability's existing browser CRUD journey requirement (delete step) to actually execute as already specified; it does not change what that requirement says.

## Impact

- `frontend-typescript/e2e/pages/BudgetListPage.ts` (test helper only)
- No production/application code changes
- Unblocks the `browser` project's CRUD journey test in the `E2E Tests` CI workflow
