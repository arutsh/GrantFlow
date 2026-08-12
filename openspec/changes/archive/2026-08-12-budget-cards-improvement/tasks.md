Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

Deviation (2026-08-12): all three groups implemented together on one branch
(`Frontend/Issue-213/archived-badge-style`) under the single ticket #213,
landing as one combined PR instead of three sequential ones.

## 1. Archived status badge treatment — no dependency on other groups

- [x] 1.1 Create a GitHub ticket for this group (`scripts/new-issue.sh`), branch on creation, move to In Progress.
- [x] 1.2 In `constants/budgetStatus.ts`, change `STATUS_STYLES.archived` from a solid fill to a dashed-outline style (transparent/white background, dashed border, muted text color); leave `draft`, `ai_draft`, `confirmed` unchanged.
- [x] 1.3 In `BudgetViewHeader.tsx`'s `StatusBadge`, add an optional icon slot rendered instead of the dot for `archived` (small archive-box icon), keeping the dot for the other three statuses.
- [x] 1.4 Verify the badge renders correctly everywhere `StatusBadge` is used (budget detail header, `CardsView`, `TableView` if applicable) — archived should look distinctly different from draft in each location.
- [x] 1.5 Run frontend lint/typecheck and the relevant component tests clean; open PR with `Closes #<n>`; PR merged.
  - [x] eslint clean on touched files, tsc -b clean
  - [x] Budgets test suite clean (151 passed)
  - [ ] PR opened and merged (combined PR, Closes #213)

## 2. Budget card actions: confirm delete + touch targets — no dependency on other groups

- [x] 2.1 Create a GitHub ticket for this group, branch on creation, move to In Progress. (folded into #213, same branch)
- [x] 2.2 In `CardsView.tsx`, replace the `bg-slate-50` footer strip and `secondary`/`danger` `Button` pair with a 2-column grid footer (Edit | Delete), each cell a minimum 44px tall.
- [x] 2.3 Give Edit a quiet/ghost style (no heavy border) and Delete a text/icon-only red style that only fills on hover/press.
- [x] 2.4 Replace the direct `onDelete(budget.id)` wiring with the existing `ConfirmDeleteButton` component so Delete requires an inline Yes/No confirmation before the delete request fires.
- [x] 2.5 Confirm cancelling the inline confirmation (tapping No) returns the card to its normal state without issuing a delete request.
- [x] 2.6 Run frontend lint/typecheck and the relevant component tests clean; open PR with `Closes #<n>`; PR merged.
  - [x] eslint clean on touched files, tsc -b clean
  - [x] Budgets test suite clean (151 passed)
  - [ ] PR opened and merged (combined PR, Closes #213)

## 3. Mobile filter collapse and shared chip colors — no dependency on other groups

- [x] 3.1 Create a GitHub ticket for this group, branch on creation, move to In Progress. (folded into #213, same branch)
- [x] 3.2 In `budgets.tsx`, below the `lg` breakpoint, replace the three full-width Status/Currency/Duration dropdown buttons with a single "Filters" trigger button.
- [x] 3.3 Add an active-filter-count badge to the "Filters" trigger, computed from `filterStatuses.length + filterCurrencies.length + (filterDuration ? 1 : 0)`.
- [x] 3.4 Implement the filter sheet: opens on tapping "Filters", contains the Status/Currency/Duration groups (reusing existing selection state and handlers) plus Clear and Apply controls, and closes on Apply, backdrop tap, or dismissal.
- [x] 3.5 Confirm the `lg`-and-above layout is unchanged (existing single-row Status/Currency/Duration controls, no "Filters" trigger).
- [x] 3.6 Update the removable status filter chips to read their colors from `STATUS_STYLES`/`STATUS_ACCENT` (`constants/budgetStatus.ts`) instead of the hardcoded yellow/green/red/slate classes.
- [x] 3.7 Manually verify on a mobile viewport (or emulated width `<1024px`) that budget cards are visible without scrolling past the filter bar.
- [x] 3.8 Run frontend lint/typecheck and the relevant component tests clean; open PR with `Closes #<n>`; PR merged.
  - [x] eslint clean on touched files, tsc -b clean
  - [x] Budgets test suite clean (151 passed)
  - [ ] PR opened and merged (combined PR, Closes #213)
