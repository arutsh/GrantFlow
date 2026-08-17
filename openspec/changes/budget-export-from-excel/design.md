## Context

`services/budget/app/` already contains a half-built "donor mapping" subsystem from an earlier attempt at this exact problem: `mapping.py`/`budget_templates.py` (models, migrated), `template_detection/` (Excel parsing), `mapping_service.py` (label matching), `mapping_routes.py` (mounted at `/api/v1/donor-mapping/*` in `main.py`, but not wired into any gateway config and never called from the frontend).

Testing the existing pipeline against a real donor spreadsheet already in the repo (`uploads/budget/Donor_budget_template.xlsx`) surfaced a hard failure, not just a coverage gap: `ExcelStructureDetector.filter_out_formula_rows()` drops an entire row if *any* cell in it is a formula. This file — like most real budget templates — has a computed second-currency column (`NOK = EUR × 8`), so nearly every line item row contains a formula somewhere and gets dropped wholesale. The cleaned output kept section titles and metadata but **zero line-item amounts**. Separately, `mapping_service.py`'s rule-based/embedding matching (`rule_based_suggestion`, `suggest_semantic_mapping`, local `sentence-transformers` embeddings cached in Redis) is a reasonable cost-conscious pattern, but it operates on column headers that were never reliably extracted in the first place on this file's layout (two sections on one sheet, no header row for the detailed-budget section, numbered-outline categories). Hardening the extraction/matching heuristics to handle this file, and the next donor's differently-shaped file, and the one after that, is open-ended work with no natural stopping point.

This design replaces that matching-based approach with AI-first extraction, and retires the parts of the dormant subsystem it supersedes rather than leaving a second orphaned layer next to the first.

## Goals / Non-Goals

**Goals:**
- Import an org's own-format `.xlsx` budget into a populated `ai_draft` GrantFlow budget with zero required user setup (no mandatory column-mapping step before the first extraction attempt).
- AI extraction works regardless of whether the org has BYOK configured: prefer the org's own provider key, fall back to a GrantFlow-funded cheap model when none is configured, so import quality doesn't depend on setup. This is a deliberate, scoped carve-out from the platform's BYOK-only/no-fallback policy, decided 2026-08-17 for this feature specifically.
- Extract everything resolvable; never drop unresolved data — land it in `extra_fields` instead of blocking the import.
- Recognize a donor's template layout once — by any organization, not just the one that first uploaded it — and skip AI entirely on a fingerprint match, via a shared, named template identity rather than a private per-org cache.
- Lay the groundwork for a future export/regeneration change (named, versioned template identity; `BudgetModel.donor_template_id` provenance) without building export itself here.

**Non-Goals:**
- CSV / Google Sheets / multi-format import (Excel `.xlsx` only, per this proposal's scope).
- Multi-sheet reconciliation — v1 auto-picks one primary sheet (reusing the old `is_primary` heuristic: name in `{"budget", "summary"}`, else first sheet) and ignores the rest.
- **Exporting a budget back into a donor's exact Excel layout.** This is a real, larger feature (regenerating a formatted file, not reading one) deferred to a follow-on change. `detected_structure` here captures what's needed to re-extract lines from a matching layout; it is not guaranteed sufficient for pixel/format-faithful regeneration — that's the follow-on change's problem to define.
- Fuzzy "this looks like a new version of an existing template" detection. `DonorTemplateModel.version` exists in the schema so the follow-on export work doesn't need another migration, but v1 only does exact-fingerprint matching — no version-diffing logic.
- A dedicated template-browsing/management UI. Templates are created implicitly via an optional post-confirm "save as template" prompt; no admin CRUD screen in this change.
- Rule-based/local-embedding field matching as a resolution mechanism — superseded by AI-first extraction. The dormant `mapping_service.py` apparatus and the models that only existed to support it are removed, not revived.
- Cross-org template sharing controls beyond fingerprint matching — any org matching a fingerprint gets the fast path; there's no per-donor access control or template ownership model in this change.

## Decisions

**1. AI-first full-line extraction, not column-header matching.** A cleaned dump of the sheet (via the hardened `spreadsheet_reader.py`, see Decision 2) is sent to a single structured-output AI call that returns `category`/`description`/`amount`/`currency` per line directly, plus a confidence signal. This replaces resolving column roles one header at a time — the real-file test showed the failure mode is in row/cell extraction and section structure, not label matching, so a smarter matcher wouldn't have helped. One call handles arbitrary real-world layouts (multi-section sheets, implicit headers, numbered category outlines) without new heuristics per donor.

**2. Revive `ExcelStructureDetector`, fix its formula-row bug, retire `detector.py`.** `spreadsheet_reader.py`'s pandas-based cleaning pipeline is the right foundation, but `filter_out_formula_rows` must exclude formula **cells**, not whole rows — the current whole-row drop is what caused 100% data loss on the sample file. `detector.py`'s total/grand-total row detection (`detect_totals`, `classify_row`'s total patterns) is worth porting into the fixed pipeline as a pre-filter (fewer rows sent to the AI call = lower cost) before the file itself is deleted.

**3. `DonorTemplateModel` is a shared, named, donor-scoped template identity — not a per-organization cache.** Extend it (in `mapping.py`) with `fingerprint` (normalized header sequence, indexed), `detected_structure` (JSONB, the AI-derived extraction mapping), and `version` (int, default 1, unused by any diffing logic yet). Fingerprint lookup on upload is **global**: any organization's file matching a stored fingerprint reuses that `detected_structure` and skips the AI call, regardless of who created the template record. This is what makes a second grantee org's upload of the same donor's file free on their very first upload, and is the correct foundation for the deferred export change (which needs to export *to* a named template someone else may have defined). `BudgetModel.donor_template_id` — an existing field with no current writer — becomes the provenance link, set whenever an import matches or creates a template.

**4. No forced mapping step; `ai_draft` + `extra_fields` remain the safety valve.** Mirrors how `chat-parse-budget` already lands AI-parsed budgets in `ai_draft` for review before confirming. A line the AI extraction couldn't confidently resolve still gets created — its raw source data goes into `BudgetLineModel.extra_fields` — so the user cleans it up in the existing edit UI rather than being interrupted mid-upload.

**5. AI funding: BYOK-preferred, GrantFlow-funded cheap-model fallback.** Reuses `services/ai`'s `ResolvedModel`/provider-resolution pattern: try the org's configured key first; if none exists, use a GrantFlow-operated low-cost model so the feature works out of the box. Every call — BYOK or platform-funded — is audit-logged with funding source, token counts, and cost (extending `parse_service.py`'s `write_audit_log` pattern), and platform-funded calls get a basic per-organization rate limit, since this is now a genuine platform cost center rather than a strictly opt-in one.

**6. Retire the superseded subsystem outright.** `mapping_service.py` (rule/embedding matching), most of `mapping_routes.py` (`/suggest`, `/mappings`, `/fields*`, the debug `/ping`), `mapping_crud.py`'s field-mapping functions, and the `DonorFieldModel`/`NgoMappingModel`/`SemanticFieldMappingModel`/`UploadedTemplateModel`/`TemplateToBudgetMappingModel` models are deleted, along with their (verified empty) database tables and the `sentence-transformers`/`torch` dependencies that existed only to support them. Leaving them dormant a second time — now unreachable from *two* generations of unfinished work instead of one — has no upside; deleting them is also a real, if secondary, win: roughly 1–2GB off the budget-service image.

## Risks / Trade-offs

- **[Risk]** Sheets with merged cells, multi-row headers, or nested category hierarchies still challenge the AI extraction's confidence → **Mitigation**: partial/best-effort import into `extra_fields` rather than a hard failure; a single AI call is materially more robust to layout variance than the rule-based approach was, but not infallible.
- **[Risk]** The dormant code hardcodes a local `/app/uploads/...` path — not viable in a container/multi-instance deployment → **Mitigation**: reuse the existing `cloud-agnostic-storage` capability for the uploaded file, not local disk.
- **[Risk]** A persisted template fingerprint goes stale if a donor changes their spreadsheet layout without it being recognized as a new file → **Mitigation**: fingerprint match requires an exact normalized header/structure sequence; any mismatch forces a fresh AI extraction rather than silently reusing a stale mapping.
- **[Risk]** The AI call now sees the full cleaned sheet content (categories, descriptions, amounts), not just header labels as originally scoped → **Mitigation**: only the org's own visible cell data is sent (no other file metadata), the same data already visible to anyone with access to the budget in-app; every call is audit-logged regardless of funding source.
- **[Risk]** The platform-funded fallback is a real, currently uncapped cost center and a potential abuse surface (repeated uploads with no BYOK key) → **Mitigation**: per-organization rate limiting on platform-funded calls, cost-tagged audit logging from day one so real usage informs a cap; exact limit is an open question below.
- **[Risk]** Dropping `donor_fields`/`ngo_mappings`/`semantic_field_mappings`/`uploaded_templates`/`template_budget_mappings` is an irreversible schema change, not just code deletion → **Mitigation**: confirmed empty/unused in all environments as of this design; the drop migration should re-verify row counts are zero immediately before running.

## Migration Plan

Two migrations: (1) extend `donor_templates` with `fingerprint`, `detected_structure`, `version`; (2) drop `donor_fields`, `ngo_mappings`, `semantic_field_mappings`, `uploaded_templates`, `template_budget_mappings` after confirming they're empty. Implementation order: retire the dead code and land the schema changes first (Decision 6, Decision 3's schema half), then the AI-first extraction pipeline, then the save-as-template flow, then gateway/frontend wiring — each its own PR per `tasks.md`. Rollback for the feature itself is removing the route/entry point; the schema-drop migration is the one non-reversible step and should only run after the code that could reference those tables is already gone.

## Open Questions

- What per-organization rate limit / cost cap should apply to the platform-funded fallback? Not yet defined — needs a number before this ships broadly, informed by early audit-log data if possible.
- Max accepted file size / row count for an uploaded sheet — not yet defined.
- Should the primary-sheet auto-pick heuristic (`name in {"budget","summary"}`, else first sheet) be exposed as a user override if wrong, or is re-upload with a renamed sheet an acceptable fix in v1?
