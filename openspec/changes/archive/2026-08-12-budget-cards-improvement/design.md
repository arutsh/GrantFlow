## Context

`frontend-typescript/src/pages/Budgets/budgets.tsx` and its `CardsView`/`BudgetViewHeader` components render the budgets list. A mockup (reviewed with the user, artifact `ea188718-474c-44a2-9a28-4d6141081122`) validated three fixes: a distinct `archived` badge treatment, a lighter/confirmed card-action footer, and a mobile filter bar collapsed behind a single trigger. This is a single-page, frontend-only change — no new dependencies, no API changes, no data model changes.

## Goals / Non-Goals

**Goals:**
- Make `archived` visually distinct from `draft` at a glance, without adding a new hue to an already grey-heavy status palette.
- Give card actions real touch targets (44px) and a confirm step before delete.
- Get budget cards visible above the fold on mobile viewports (`<lg`, matches the existing `md`/`lg` breakpoints already used in `budgets.tsx` and `CardsView.tsx`).

**Non-Goals:**
- No change to `TableView` (desktop-only, not touched by this proposal).
- No change to filter *logic* (`filteredData` memo, `uniqueStatuses`/`uniqueCurrencies`) — only how the controls are presented and grouped.
- No dark mode — the app has none today; not introduced here.

## Decisions

**Archived badge: dashed outline + icon, not a new fill color.** `STATUS_STYLES` already assigns slate/amber/teal to draft/ai_draft/confirmed; adding a fourth *fill* color risks the same near-collision problem recurring as statuses are added later. A structural difference (outline vs. fill) scales better than hunting for a fourth distinguishable hue. Alternative considered: switching `archived` to a distinct hue (e.g. violet) — rejected because it implies a semantic category ("this is a kind of state") rather than "this is inactive," which the dashed/outline treatment communicates directly.

**Reuse `ConfirmDeleteButton` rather than a new confirm pattern.** `components/ui/Button.tsx` already exports `ConfirmDeleteButton` (inline Yes/No swap) and it's used elsewhere in the app. `CardsView.tsx` currently calls `onDelete` directly from a plain `danger`-variant `Button`. Swapping to the existing component is a one-line change and keeps the confirm interaction consistent app-wide, instead of inventing a card-specific modal or a second confirm pattern.

**Mobile filter bar: single "Filters" trigger + bottom sheet, gated at the existing `lg` breakpoint.** `budgets.tsx` already branches mobile/desktop behavior off `window.innerWidth < 768` (`isMobile` state, used for the cards/table auto-switch) and off Tailwind's `lg:` prefix in the filter row's own classes. Reusing `lg:` (not introducing a second breakpoint) keeps the filter bar and the cards/table toggle changing at consistent points. Alternative considered: keep the three dropdowns but shrink them — rejected, doesn't fix the fold problem, just delays it by a row or two.

**Filter chip colors: source from `STATUS_STYLES`/`STATUS_ACCENT`, not a second hardcoded palette.** `budgets.tsx` currently hardcodes yellow/green/red/slate for the removable status chips, independent of `constants/budgetStatus.ts`. Pointing the chips at the same constants means a future status color change (e.g. if `archived`'s treatment changes again) only happens in one file.

**No new state management.** The bottom sheet's open/closed state is a simple boolean alongside the existing `showStatusDropdown`/`showCurrencyDropdown`/`showDurationDropdown` state — those three collapse into the groups rendered *inside* the sheet rather than being replaced by new machinery.

## Risks / Trade-offs

- **Touch target change shrinks visual weight of Delete, which is a destructive action.** → Mitigated by keeping the confirm-on-tap step (`ConfirmDeleteButton`) so a mis-tap is not itself destructive.
- **Collapsing three dropdowns into one sheet is a bigger interaction change than the color/spacing fixes.** → Scope the sheet to mobile only (`<lg`); desktop behavior is unchanged, limiting blast radius to the viewport where the current layout is actually broken.
- **`StatusBadge`'s new icon slot is only used by one status today.** → Keep it as an optional prop rather than a per-status icon map, so it doesn't need to be filled in for draft/ai_draft/confirmed.

## Migration Plan

Frontend-only, no data migration. Ship as a normal PR; no feature flag needed since behavior is additive/cosmetic and reversible by revert.
