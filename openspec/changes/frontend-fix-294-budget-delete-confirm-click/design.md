# Design

## Context

See proposal.md - Why. This is a single-file, single-method fix in a Playwright page object; none of the triggers for a fuller design doc (cross-cutting change, new dependency, data model change, security/perf/migration complexity) apply here.

## Goals / Non-Goals

**Goals:**
- Make `BudgetListPage.deleteBudget()` actually complete the delete flow the UI requires (click delete, then confirm).

**Non-Goals:**
- Changing the underlying `ConfirmDeleteButton` UX or the archive-vs-hard-delete product behavior.
- Adding a dedicated `confirmDelete()` page-object method — one extra click inline is proportionate to the size of this fix.

## Decisions

- Add the "Yes" click directly inside `deleteBudget()` rather than exposing a separate confirmation step, since every current caller of `deleteBudget()` wants the delete to fully complete and there's no case where a caller wants to stop at "pending confirmation".
- Locate the "Yes" button scoped to the same row (`this.row(name).getByRole("button", { name: "Yes" })`) rather than a bare page-level `getByRole`, so the click can't accidentally hit a Yes/No pair open on a different row.

## Risks / Trade-offs

- [Confirmation button text changes later] → Low risk; it's a static UI string in `ConfirmDeleteButton`'s own render, easy to keep in sync since a text change would need a page-object update anyway for the "Delete budget" title too.
