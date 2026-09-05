One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Grouped/Simple view toggle (desktop only)

- [ ] 1.1 In `frontend-typescript/src/components/ui/Table.tsx`, change `TableCommon`'s hardcoded `initialState: { grouping: ["category"] }` to a `grouping?: string[]` prop (default `["category"]` when omitted) fed into `useReactTable`'s controlled state, so callers can pass `[]` to disable grouping. No visible behavior change for existing callers that don't pass the prop.
- [ ] 1.2 In `frontend-typescript/src/pages/Budgets/components/BudgetViewLinesTable.tsx`, add `viewMode` state (`useState<"grouped" | "simple">("grouped")`), same ephemeral local-state pattern as the existing `displayMode` currency toggle (not persisted).
- [ ] 1.3 Add a "Grouped / Simple" `role="group"` toggle next to the existing Local/Donor/Both currency toggle, reusing `Button variant="toggle"`; render/show it only in the desktop block, since it has no effect on mobile.
- [ ] 1.4 Pass `grouping={viewMode === "grouped" ? ["category"] : []}` from `BudgetViewLinesTable` into `TableCommon`. Leave the mobile card rendering block untouched.
- [ ] 1.5 Add tests to `BudgetViewLinesTable.test.tsx`: Grouped (default) shows subtotal rows; Simple shows a flat list with no subtotal rows; toggle exposes `role="group"`; mobile rendering is unaffected by `viewMode`.
- [ ] 1.6 Run frontend typecheck/build and test suite clean; PR merged (`Closes #<ticket>`).

## 2. Inline category rename — depends on 1 (shares `TableCommon` changes) and on `budget-category-scoping`'s `PATCH /budget-categories/{id}` route + `BudgetCategoryUpdate` schema being merged

- [ ] 2.1 Confirm `budget-category-scoping` is merged (route, schema, and frontend `BudgetCategory` type with `budget_id` all exist) before starting this group.
- [ ] 2.2 Add `updateBudgetCategory(categoryId, updates: { name?: string; code?: string })` to `frontend-typescript/src/api/gatewayApi.ts`, `PATCH budget-categories/${categoryId}`, matching the existing `updateBudgetLines` pattern.
- [ ] 2.3 Extend `TableCommon` (`Table.tsx`) with an optional `renderGroupExtra?: (row) => ReactNode` prop, rendered next to the existing `(count)` badge in the grouped-row branch. Omitting it preserves today's exact rendering.
- [ ] 2.4 In `BudgetViewLinesTable.tsx`, pass a `renderGroupExtra` renderer showing a pencil (`Edit2`) button beside the category group name (desktop). Clicking swaps the name to a controlled inline text input; Enter/blur confirms, Escape cancels. Derive the category id from `row.subRows[0]?.original?.category`; hide the affordance for the "—" (uncategorized) group and whenever `readOnly` is true.
- [ ] 2.5 Add the same pencil/inline-edit affordance to the mobile category header (`BudgetViewLinesTable.tsx`'s hand-rolled grouped card header) — mobile stays always-grouped but still gets rename, since only the Simple/Grouped *toggle* is desktop-only, not rename itself.
- [ ] 2.6 Wire the rename confirm action to a `useMutation` calling `updateBudgetCategory`; on success, update `budget.lines[*].category.name` for every line sharing that category id via `setBudget` (mirror `AddBudgetLine.tsx`'s post-edit `onSuccess` mapping). On a duplicate-name (400) rejection, keep the input open and show the error inline instead of reverting silently.
- [ ] 2.7 Add tests to `BudgetViewLinesTable.test.tsx`: pencil shown only when editable and category is real (desktop + mobile); confirming edits submits the `PATCH` with the new name and updates the displayed name on success; Escape cancels without a request; a duplicate-name error surfaces inline and leaves the name unchanged.
- [ ] 2.8 Run frontend typecheck/build and test suite clean; PR merged (`Closes #<ticket>`).
