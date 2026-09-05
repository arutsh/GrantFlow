## Context

The Budget Lines table (`BudgetViewLinesTable.tsx`) renders via a shared, generic `TableCommon` component (`components/ui/Table.tsx`) that currently hardcodes `initialState: { grouping: ["category"] }` — every consumer is always grouped by category, with no way to opt out, and no way to customize what renders in a group's header row. This change adds two independent, additive UI features on top of that: an inline rename affordance on the category group header, and a toggle to turn grouping off entirely (desktop only). Both depend on `budget-category-scoping` having landed its `PATCH /budget-categories/{id}` route and `BudgetCategoryUpdate` schema — this change adds no backend code of its own.

## Goals / Non-Goals

**Goals:**
- Let a user rename a budget category's name inline, from the Budget Lines view, without leaving the page.
- Let a user switch the desktop Budget Lines table between grouped-by-category (current, default) and a flat simple list.
- Keep `TableCommon` generically reusable — grouping and group-header customization become opt-in props with backward-compatible defaults, not budget-specific logic baked into the shared component.

**Non-Goals:**
- No mobile change: the mobile card layout stays always-grouped, unchanged, no Grouped/Simple toggle there.
- No category creation/deletion UI (only rename).
- No persistence of the Grouped/Simple choice across sessions — same ephemeral, local-state footprint as the existing Local/Donor/Both currency toggle.
- No backend/schema changes — this change is a pure consumer of `budget-category-scoping`'s API surface.

## Decisions

**Rename UX: inline edit, not a modal.** A pencil icon next to the category name in the group header swaps it for a text input in place (Enter/blur saves, Escape cancels). Chosen over a modal dialog for a single-field edit — less UI to build, and matches the direct, no-modal interaction style already used elsewhere in this view (the currency toggle, the delete-confirmation button).

**Category id at the group header.** TanStack's grouped rows only expose the group *value* (the category name string) to the header renderer, but the rename mutation needs the category id. Desktop pulls it from `row.subRows[0]?.original?.category`. The "—" (uncategorized) group has no real category, so the rename affordance is simply not shown there.

**`TableCommon` grows two opt-in props instead of a category-specific fork.**
- `grouping?: string[]` (default `["category"]` when omitted) replaces the hardcoded `initialState`, feeding `useReactTable`'s controlled state so a caller can pass `[]` to disable grouping entirely.
- `renderGroupExtra?: (row) => ReactNode` renders next to the existing `(count)` badge in the grouped-row branch, letting `BudgetViewLinesTable` inject the rename pencil without teaching the generic table component about budget categories.

Both default to today's exact behavior when omitted, so no other `TableCommon` consumer is affected.

**Optimistic local update on rename success.** Renaming updates `budget.lines[*].category.name` for every line sharing that category id via the existing `setBudget`/React Query cache update path (same pattern `AddBudgetLine.tsx` already uses after a line edit), rather than refetching the whole budget — keeps the table in sync immediately without an extra round trip.

**Grouped/Simple toggle scoped to desktop only.** Mobile's grouped rendering is a separate, hand-rolled JSX branch (not `TableCommon`), always-expanded by design; adding a flat mode there would mean building and testing a second rendering path for comparatively little value at small mobile screen widths. The toggle itself is hidden/inert on mobile.

## Risks / Trade-offs

- **[Risk]** Renaming a category to a name that already exists in the same budget fails server-side (`400`, unique `(budget_id, name)` constraint) → **Mitigation**: surface the API's error message inline near the input rather than silently reverting; the input stays editable so the user can pick a different name.
- **[Risk]** `TableCommon`'s new props could silently change behavior for a future second consumer if defaults are wrong → **Mitigation**: defaults exactly reproduce current hardcoded behavior (`grouping = ["category"]`, no extra header content); covered by existing/extended tests.
- **[Trade-off]** No mobile flat view means mobile and desktop offer different capabilities for this one toggle — acceptable per the explicit scope decision to keep mobile unchanged.

## Migration Plan

Frontend-only, no data migration. Ships behind no flag — both features are additive UI (a new toggle, a new pencil icon) with safe defaults, so this can go out as a normal PR once `budget-category-scoping` is merged. Rollback is a plain revert.
