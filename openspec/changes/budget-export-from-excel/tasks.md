One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Retire dormant mapping subsystem; AI-first Excel extraction core

- [ ] 1.1 Port `detector.py`'s total/grand-total row detection heuristics (`detect_totals`, the `classify_row` total patterns) into a hardened `spreadsheet_reader.py`, then delete `services/budget/app/services/template_detection/detector.py`
- [ ] 1.2 Fix `spreadsheet_reader.py`'s `filter_out_formula_rows` to exclude formula **cells** individually rather than dropping the whole row — this bug currently discards 100% of line items on realistic templates with a computed second-currency column
- [ ] 1.3 Delete `mapping_service.py`'s rule/embedding matching apparatus (`rule_based_suggestion`, `suggest_mapping`, `suggest_semantic_mapping`, `_match_unknown_fields`, the embedding/Redis caching helpers) — superseded by AI-first extraction
- [ ] 1.4 Delete `mapping_routes.py`'s `/suggest`, `/mappings`, `/mappings/by-ngo/{ngo_id}`, `/fields`, `/fields/bulk`, `/fields/{template_id}`, and debug `/ping` endpoints; delete `mapping_crud.py`'s field-mapping CRUD functions; delete `mapping_schema.py`'s field/mapping/suggestion schemas; keep and adapt only the `DonorTemplateModel`-related CRUD
- [ ] 1.5 Delete `DonorFieldModel`, `NgoMappingModel`, `SemanticFieldMappingModel` (`mapping.py`) and `UploadedTemplateModel`, `TemplateToBudgetMappingModel` (`budget_templates.py`); delete `test_mapping_routes_wiring.py` (tests the deleted routes)
- [ ] 1.6 Write a migration dropping the now-dead `donor_fields`, `ngo_mappings`, `semantic_field_mappings`, `uploaded_templates`, `template_budget_mappings` tables — re-verify they're empty in all environments immediately before the drop runs
- [ ] 1.7 Remove `sentence-transformers` and `torch` from budget-service `requirements.txt`; remove `redis` too if nothing else in the service uses it
- [ ] 1.8 Extend `DonorTemplateModel` with `fingerprint` (indexed string), `detected_structure` (JSONB), and `version` (int, default 1) via migration
- [ ] 1.9 Store the uploaded `.xlsx` via the existing cloud-agnostic storage capability (not local disk)
- [ ] 1.10 Implement the extraction pipeline: clean the sheet via the fixed `spreadsheet_reader.py`, compute a structure fingerprint, look up any `DonorTemplateModel` with a matching fingerprint (global lookup, not scoped to the uploading organization) — if found, extract lines directly from its `detected_structure`; otherwise call a new AI-service extraction capability
- [ ] 1.11 Add the AI-service extraction capability: a structured-output PydanticAI call (following `parse_service.py`'s pattern) that returns category/description/amount/currency per line from a cleaned sheet dump, BYOK-preferred with a GrantFlow-funded cheap-model fallback when no provider key is configured
- [ ] 1.12 Add cost-tagged audit logging for every AI extraction call (funding source, tokens, cost, duration), matching `parse_service.py`'s `write_audit_log` pattern; add a per-organization rate limit on GrantFlow-funded calls
- [ ] 1.13 Route unresolved/low-confidence extraction results into `extra_fields` on the produced line rather than dropping them
- [ ] 1.14 Implement `POST /budgets/import-excel`: accept a multipart `.xlsx` upload, run the pipeline above, call `create_budget_with_lines_service` with `status: ai_draft`, setting `BudgetModel.donor_template_id` when a template was matched
- [ ] 1.15 Add tests: valid-file happy path, invalid/corrupt file rejection, total-row exclusion, unresolved-data `extra_fields` passthrough, fingerprint match skips AI, no-provider-key falls back to the platform-funded model, platform-funded call failure fails gracefully, rate limit enforced
- [ ] 1.16 Run budget and ai service tests/lint clean; PR merged

## 2. Save-as-template flow — depends on 1

- [ ] 2.1 On budget confirmation (existing confirm transition on `PATCH /budgets/{id}`), if the budget originated from an Excel import with no matched template (a fresh AI extraction) and its lines were not edited since creation, surface an optional "save as reusable template" action
- [ ] 2.2 On save, create a new `DonorTemplateModel` (with the computed fingerprint and `detected_structure`, user-provided name) and set the originating budget's `donor_template_id` if not already set
- [ ] 2.3 Add tests: the save option only appears for unmatched, unedited, Excel-originated `ai_draft` budgets; saving creates a reusable template; a subsequent upload with the same fingerprint (by the same or a different organization) then skips AI extraction
- [ ] 2.4 Run budget service tests/lint clean; PR merged

## 3. Gateway wiring and frontend upload entry point — depends on 1, 2

- [ ] 3.1 Add the `/budgets/import-excel` route to `nginx-dev.conf`, `nginx.conf`, and `Caddyfile`
- [ ] 3.2 Add an "Import from Excel" upload entry point (button + file picker) to the budget list view
- [ ] 3.3 On successful upload, navigate to the created `ai_draft` budget's single-budget view so the user lands on the existing confirm/edit review flow
- [ ] 3.4 Add the optional "save as reusable template" prompt UI on confirm, wired to group 2's backend action
- [ ] 3.5 Handle and surface upload/parse errors (invalid file, parse failure, rate limit) in the UI without a partial or broken navigation
- [ ] 3.6 Manually verify end-to-end with a handful of real-shaped org spreadsheets in staging before enabling for all orgs
- [ ] 3.7 Run frontend and budget service tests/lint clean; PR merged
