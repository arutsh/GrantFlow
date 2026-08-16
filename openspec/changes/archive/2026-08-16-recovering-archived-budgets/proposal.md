## Why

Archiving a budget (the delete button on the budgets list) is a one-way status flip in the current API — `update_budget_service` only allows the `confirmed` status as a target when the budget is currently `draft` or `ai_draft`, so an accidentally archived budget cannot be un-archived through the app. Recovering one today requires a direct database UPDATE, which isn't something a non-technical org admin can do and isn't safe to repeat routinely.

## What Changes

- Add a "Restore" action for `archived` budgets that transitions them back to an active status without going through the normal draft→confirm flow.
- Add backend support for this transition: a new allowed path in the budget status state machine (`archived` → restored status), separate from the existing `is_confirm_attempt` guard so restoring doesn't require re-validating confirm-only preconditions (e.g. re-checking `start_date`) that were already satisfied before archiving.
- Restore target status is inferred from data already on the row: if `confirmed_at` is set, restore to `confirmed`; otherwise restore to `draft`. This is a heuristic, not an exact replay — see Open Questions.
- Surface the Restore action in the budgets list UI, visible only on `archived` cards, alongside the existing status badge treatment.

## Capabilities

### New Capabilities
- `budget-restore`: backend rule and service support for transitioning a budget from `archived` back to an active status, plus the UI action that triggers it.

### Modified Capabilities
- `budget-list-ui`: archived budget cards gain a "Restore" action alongside the existing delete/archive action.

## Impact

- Backend: `services/budget/app/services/budget_services.py` (`update_budget_service`, `_resolve_updatable_budget`), `services/budget/app/crud/budget_crud.py`.
- Frontend: `frontend-typescript/src/api/budgetApi.ts` (new `restoreBudget` call), `frontend-typescript/src/pages/Budgets/budgets.tsx` and card components.
- Open question (not resolved by this change): archived budgets may have associated currency ledger entries (`budget-currency-ledger`) and reports (`budget-reports`) that were frozen or otherwise affected at archive time. This proposal does not define what happens to that ledger/report state on restore — whether it resumes as-is, needs revalidation, or requires its own recovery step. Needs a decision before backend implementation.
