## Why

PR #279 added the Grouped/Simple toggle and inline category-rename control to the Budget Lines view. On mobile, the rename control was inlined into the category header row with no space to grow into, so opening it (or hitting a long category name) overflows the row and clips the subtotal/used-% on narrow viewports. Separately, the toggle's "Simple" label reads as a peer of the Local/Donor/Both currency pills next to it rather than a distinct grouping control, and its mobile-hidden behavior is currently accidental (CSS-only) rather than a documented contract. A fourth issue surfaced during review: each mobile line-item card ends with a dedicated row holding only its Edit/Delete icons, disconnected from the amount they act on and costing ~30px of dead height per line with no information in it.

## What Changes

- Rename the desktop Grouped/Simple toggle's "Simple" option to "List" (label + tooltip text only — the `viewMode` value stays `"simple"` internally, no API/state contract change).
- Fix the mobile category-header overflow: the category name gets `min-w-0 flex-1 truncate`, and the header row wraps instead of clipping, so a long name or an open rename input never pushes the subtotal/used-pill off-card.
- Document (in spec + a short code comment) that mobile intentionally never shows the Grouped/Simple toggle and always renders grouped-by-category — codifying the current incidental behavior as a deliberate one.
- Move the mobile line-item card's Edit/Delete icon buttons out of their own dedicated row and inline them into the row that already shows the amount, deleting the now-empty icon-only row. Chosen as the simplest of four candidate layouts compared (trailing icon rail vs. overflow menu vs. swipe-to-reveal vs. tap-to-expand sheet) — it reuses the existing buttons and handlers with no new interaction pattern to build.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `budget-lines-grouping-ui`: the "Simple" toggle option is renamed to "List" in its requirement/scenario text; the existing "mobile is unaffected by the toggle" requirement is unchanged but reaffirmed; adds a requirement that the mobile line-item card places Edit/Delete inline with the amount rather than in a separate row.
- `budget-category-rename-ui`: adds a requirement that the inline rename control on mobile does not overflow its category header row (name truncates, row wraps) regardless of name length or rename-input state.

## Impact

- `frontend-typescript/src/pages/Budgets/components/BudgetViewLinesTable.tsx`: `SegmentedToggle` options (label/title text), mobile category header JSX (~line 622-636), mobile line-item row JSX (~line 660-712).
- No backend, API, or persisted-state changes. No change to `viewMode`'s internal values ("grouped" | "simple"), only its displayed label.
- Existing tests in `BudgetViewLinesTable.test.tsx` that assert on the "Simple" label text, or on the Edit/Delete icon row's structure, will need updating.
