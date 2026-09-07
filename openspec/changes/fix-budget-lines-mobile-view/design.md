## Context

`BudgetViewLinesTable.tsx` renders two parallel layouts gated by Tailwind breakpoints: a desktop `TableCommon` (`hidden sm:block`) and a hand-rolled mobile card list (`sm:hidden`). The mobile card list groups by category unconditionally — it never reads `viewMode` — while the `SegmentedToggle` control that sets `viewMode` is itself `hidden sm:inline-flex`. `CategoryRenameControl` (added in #279) is inlined into both the desktop `TableCommon`'s group-header slot and the mobile category-header `<span>`. The desktop slot has room to grow; the mobile header row (`flex items-center justify-between`, no `min-w-0`/`truncate`/`flex-wrap`) does not, so a long category name or an opened rename input (fixed `w-36` text input plus confirm/cancel buttons) overflows the row and pushes the subtotal/used-pill out of the visible card width. This is a straightforward single-file CSS/JSX fix; no architectural or data changes are involved.

## Goals / Non-Goals

**Goals:**
- Mobile category header degrades gracefully (truncates or wraps) regardless of category-name length or rename-input open/closed state.
- "Simple" → "List" is a pure label/tooltip change; `viewMode`'s internal values, persisted state, and API contract are untouched.
- The "mobile always grouped, toggle never shown" behavior becomes a documented, intentional contract (spec + comment), not incidental CSS.

**Non-Goals:**
- No redesign of the mobile card list's overall visual structure (category header + subtotal + line rows) — it already matches the desired layout; the only structural change is relocating the existing Edit/Delete icons within a line row, not restyling the card system.
- No change to `SegmentedToggle`'s visual style (segmented sliding-thumb icons) — an earlier design exploration considered alternative toggle shapes (switch, ghost icon pair, capsule) but the user only asked for the label swap, not a component swap.
- No mobile-specific "Simple" (flat/ungrouped) view — explicitly out of scope per existing `budget-lines-grouping-ui` spec.
- No new interaction pattern for Edit/Delete (no popover, gesture, or modal sheet) — see the icon-rail decision below.

## Decisions

- **Truncate + wrap over moving the rename control**: give the category-name `<span>` `min-w-0 flex-1 truncate` and let the header row `flex-wrap` instead of relocating `CategoryRenameControl` to its own line unconditionally. Truncation keeps the common case (short names) visually identical to today; wrapping only kicks in for the rare long-name/open-rename case, so no layout shift for the vast majority of budgets. Considered: always stacking the rename control below the name on mobile — rejected, since it changes the common-case layout for a rare-case problem.
- **Label-only rename for Simple → List**: change `label`/`title` strings in the `SegmentedToggle` options array only. Considered: renaming the `viewMode` union value itself (`"simple"` → `"list"`) — rejected, it would touch persisted/URL state (if any), tests, and every call site for a purely cosmetic change with no functional upside.
- **Codify mobile-hidden as spec, not new logic**: no new conditional is added to force grouping on mobile — that already happens because the mobile branch never reads `viewMode`. The change is a spec scenario + a one-line code comment recording that this is deliberate, so a future edit doesn't "fix" it into reading `viewMode` and accidentally need a mobile Simple view no one asked for.
- **Trailing icon rail over overflow menu / swipe / tap-sheet for Edit/Delete**: move the existing `Button variant="icon"` (Edit2) and `ConfirmDeleteButton` (Trash2) into the row that already renders the amount, and delete the now-empty icon row. Four candidates were mocked up and compared: an overflow (kebab) menu, swipe-to-reveal, and tap-row-for-detail-sheet were all rejected because each requires building a new UI primitive (popover, touch-drag gesture handling, or a modal sheet) to solve a problem that is really just "these two buttons are on the wrong row." The trailing rail reuses the existing buttons, handlers, and confirm-before-delete flow unchanged — smallest diff, lowest implementation risk, no new pattern for a five-person team to learn.

## Risks / Trade-offs

- [`truncate` on the category name hides the full name on mobile when it's long] → acceptable: the full name is still visible via the rename input itself when opened, and this matches how category names already truncate in other constrained UI (e.g. desktop table cells).
- [Existing `BudgetViewLinesTable.test.tsx` assertions on the literal text "Simple" will fail after the rename] → mitigation: update those assertions as part of this change's tasks.
- [A long description plus the amount+two-icons cluster could crowd the right edge of a narrow card] → mitigation: the description `<span>` gets the same `min-w-0`/wrap treatment as the category name so the trailing cluster (`flex-shrink-0`) is never pushed off-card.
