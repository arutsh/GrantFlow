## Why

The budgets list (cards view) has three usability problems, confirmed against a mockup review: the `draft` and `archived` status pills are visually indistinguishable (`bg-slate-100`/`bg-gray-200` at similar lightness/text weight), the card action buttons (a thick-bordered "Edit" next to a solid-red "Delete") are heavier than the rest of the card and fire delete with no confirmation step, and on mobile the search bar plus three full-width filter dropdowns push every budget card below the fold. GrantFlow's primary users work from a phone in the field, so the mobile filter bar in particular blocks the core "find my budget" task.

## What Changes

- Give the `archived` status pill a dashed-outline + archive-icon treatment instead of a solid grey fill, so it's structurally distinct from `draft` rather than relying on a similar hue.
- Replace the budget card's footer (bordered "Edit" + solid-red "Delete") with an even, 44px-tall two-button split using quiet/ghost styling, and wire the card's delete action through the existing `ConfirmDeleteButton` component (already used elsewhere, not currently used on this card) so delete requires an inline Yes/No confirmation.
- On mobile (`< lg` breakpoint), collapse the Status/Currency/Duration filter dropdowns into a single "Filters" trigger button showing an active-filter count badge, which opens a bottom sheet containing all three filter groups plus Clear/Apply actions. Desktop (`lg+`) keeps the existing single-row filter layout.
- Recolor the removable filter chips (the "×" tags shown above the results count) to reuse `STATUS_STYLES`/`STATUS_ACCENT` from `constants/budgetStatus.ts` instead of the separate hardcoded yellow/green/red/purple/blue set, so status color meaning stays consistent across the page.

## Capabilities

### New Capabilities
- `budget-list-ui`: The budgets list page — status badge rendering, budget card layout/actions, and search/filter controls (including responsive behavior).

### Modified Capabilities
<!-- none: no existing spec currently documents this page -->

## Impact

- `frontend-typescript/src/pages/Budgets/constants/budgetStatus.ts` — `STATUS_STYLES.archived`, `StatusBadge` gains an optional icon slot.
- `frontend-typescript/src/pages/Budgets/components/CardsView.tsx` — card footer markup/styling, delete wiring.
- `frontend-typescript/src/pages/Budgets/budgets.tsx` — mobile filter bar (new "Filters" trigger + bottom sheet), filter chip colors.
- No API, schema, or backend changes. No breaking changes — purely presentational/interaction changes to an existing page.
