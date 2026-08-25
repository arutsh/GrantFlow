## Status

**Exploratory only.** This documents the donor-template matching mechanism as it exists today (shipped in `budget-export-from-excel`) and the problems found reviewing it. No implementation is planned yet — revisit and redesign before this mechanism is trusted more broadly (e.g. before real donor orgs rely on saved templates).

## Why

`budget-export-from-excel` added a "save this budget's Excel layout as a reusable donor template" feature so a repeat donor's spreadsheet can be auto-matched and mechanically re-extracted on future uploads, skipping AI extraction. A full-branch code review flagged three related problems with how that matching is currently implemented, all in the same area, that are worth solving together rather than patching individually.

## Current state (as implemented)

- `compute_structure_fingerprint()` hashes which columns are non-empty per row of the uploaded sheet — a content-shape fingerprint, not tied to a donor's identity, an organization, or the cell values themselves.
- `DonorTemplateModel` stores one row per saved template: `fingerprint`, `detected_structure` (column index mapping), `name`.
- `prepare_excel_import_service()` looks up a template by `db.query(DonorTemplateModel).filter(fingerprint == fingerprint).first()` — global across all organizations, first match wins.
- `save_budget_as_template_service()` / `_can_save_as_template()` let a user promote any budget with a fingerprint into a `DonorTemplateModel`, gated only by "lines look unedited" (itself an approximate check — see `[[project_budget_excel_import]]`), not by budget status.
- When matched, the sheet is re-extracted mechanically from `detected_structure` with no AI involvement and no user confirmation step.

## Known problems

1. **No tenant scoping.** Two unrelated organizations whose spreadsheets happen to fill the same columns collide on the same fingerprint. Org B's upload can be silently extracted using Org A's saved column mapping, with no error surfaced and no organizational boundary enforced anywhere in the lookup.
2. **No uniqueness constraint.** The `fingerprint` index (migration `000012_add_donor_template_fingerprint.py`) is non-unique, so two templates can share a fingerprint with different `detected_structure`. `.first()` resolution is then insert-order-dependent — which mapping "wins" is undefined behavior, not a deliberate choice.
3. **No review gate before promotion.** A freshly-imported, unreviewed `ai_draft` budget can be saved as a template directly (the UI only offers this after confirmation, but the service layer doesn't enforce it), so a hallucinated or wrong column mapping can become the thing every future upload of that layout mechanically replays.

## Open question (the big one)

**Is content-shape fingerprint matching the right mechanism at all, or does donor-template reuse need a fundamentally different design?**

Some directions worth weighing when this gets revisited, none chosen yet:
- Scope matching to the owning organization (or even to a specific external funder record) instead of a global index — closes problem 1, but doesn't address 2 or 3 on its own.
- Make templates explicit and user-chosen ("use my saved 'USAID Q3' template") rather than silently auto-matched by structural hash — trades convenience for predictability and removes the silent-wrong-match failure mode entirely.
- Require a one-time human confirmation of the extracted mapping before a template is eligible for future silent replay, closing problem 3 structurally instead of via a status check that can be bypassed.
- Reconsider whether "hash the column-fill shape" is a good similarity signal at all, versus something keyed on the donor/funder identity plus a versioned, explicitly-approved structure.

This needs real design thought, not a quick patch — hence a separate change rather than folding it into further fixes on `budget-export-from-excel`.
