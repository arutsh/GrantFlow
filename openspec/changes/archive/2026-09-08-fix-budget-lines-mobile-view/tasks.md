One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Fix Budget Lines mobile overflow and toggle wording

- [x] 1.1 In `BudgetViewLinesTable.tsx`'s `SegmentedToggle` options (~line 566-571), rename the `"simple"` option's `label` from `"Simple"` to `"List"` and update its `title` tooltip text accordingly; leave the `value: "simple"` union member unchanged.
- [x] 1.2 In the mobile category header (~line 622-636), add `min-w-0 flex-1 truncate` to the category-name `<span>` and `flex-wrap` (with appropriate row-gap) to its containing header row, so a long name or an open `CategoryRenameControl` input never clips or pushes the subtotal/used-% pill off-card.
- [x] 1.3 Add a short one-line comment near the mobile card list (~line 604-519) noting that mobile intentionally never reads `viewMode` and always renders grouped-by-category — codifying the existing incidental behavior as deliberate.
- [x] 1.4 Update `BudgetViewLinesTable.test.tsx` assertions that reference the literal "Simple" label text to "List".
- [x] 1.5 Add/update a test in `BudgetViewLinesTable.test.tsx` covering the mobile category-header overflow fix: a long category name renders truncated with the subtotal/used-% still present in the DOM (e.g. via `getByText`/snapshot of classes rather than pixel measurement).
- [x] 1.6 In the mobile line-item card (~line 660-712), move the existing `Button variant="icon"` (Edit2) and `ConfirmDeleteButton` (Trash2) into the row-1 flex container next to the amount `<span>`, and delete the now-empty dedicated icon row; give the description `<span>` `min-w-0`/wrap so the trailing amount+icons cluster (`flex-shrink-0`) is never pushed off-card.
- [x] 1.7 Add/update a test in `BudgetViewLinesTable.test.tsx` asserting Edit/Delete render inline with the amount (not in a separate row) for both a short and a long (wrapping) description.
- [ ] 1.8 Manually verify in a mobile viewport (~375-390px): toggle is hidden, category header with a long name and an opened rename control both stay within the card, the desktop toggle shows "Grouped"/"List", and both a short and a long line-item description keep Edit/Delete visible inline with the amount. (Not completed by Claude — the local dev server on port 3000 is a different app, not this frontend; needs the user's actual local URL to check live.)
- [x] 1.9a Run the frontend test suite clean (`npx vitest run` from `frontend-typescript/`): 39 files, 302 tests pass, including the new/updated assertions in `BudgetViewLinesTable.test.tsx`.
- [x] 1.9b PR merged (#281).
