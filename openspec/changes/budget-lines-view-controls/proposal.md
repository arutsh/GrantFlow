## Why

Budget categories currently have no rename affordance in the UI, even though the `budget-category-scoping` change (in progress) gives categories a real per-budget owner and adds the `PATCH /budget-categories/{id}` route needed to expose renaming safely — that change's proposal explicitly defers the rename UI as "a separate follow-up." Separately, the Budget Lines table is always grouped by category with no way to see a flat list, which gets awkward for budgets with many categories or few lines per category. Both are small, additive UI changes to the same view.

## What Changes

- Add an inline rename affordance for a budget category's name, shown on the category group header in the Budget Lines table (desktop and mobile), using the `PATCH /budget-categories/{id}` route from `budget-category-scoping`.
- Add a "Grouped / Simple" view toggle to the desktop Budget Lines table, alongside the existing Local/Donor/Both currency toggle, so users can switch between the current grouped-by-category layout and a flat, ungrouped list. Mobile keeps its existing always-grouped card layout, unchanged.
- **Depends on** `budget-category-scoping` merging first (specifically its `PATCH /budget-categories/{id}` route and `BudgetCategoryUpdate` schema) — no new backend work is needed here.

## Capabilities

### New Capabilities
- `budget-category-rename-ui`: inline rename of a budget category's name from the Budget Lines view, calling the existing category-scoping PATCH endpoint.
- `budget-lines-grouping-ui`: a Grouped/Simple display toggle for the desktop Budget Lines table.

### Modified Capabilities
(none — no backend requirement changes; this change is purely a frontend consumer of the category-scoping change's API surface)

## Impact

- **Frontend only**: `frontend-typescript/src/pages/Budgets/components/BudgetViewLinesTable.tsx`, `frontend-typescript/src/components/ui/Table.tsx` (generic grouping/group-header extension points), `frontend-typescript/src/api/gatewayApi.ts` (new `updateBudgetCategory` call), `frontend-typescript/src/pages/Budgets/components/BudgetViewLinesTable.test.tsx`.
- **No backend or schema changes** in this change; relies entirely on `budget-category-scoping`'s API surface.
