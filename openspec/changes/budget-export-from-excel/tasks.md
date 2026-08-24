One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Retire dormant mapping subsystem; AI-first Excel extraction core

Note: 1.10 (pipeline entry point), 1.11 (AI-service call site), and 1.14 (`POST /budgets/import-excel`) were superseded by Group 4 on 2026-08-19 — the extraction/cleaning logic they describe was kept but re-homed behind budget's `prepare-import` endpoint, with the AI-call and budget-creation moved to chat service. See Group 4.

- [x] 1.1 Port `detector.py`'s total/grand-total row detection heuristics (`detect_totals`, the `classify_row` total patterns) into a hardened `spreadsheet_reader.py`, then delete `services/budget/app/services/template_detection/detector.py`
- [x] 1.2 Fix `spreadsheet_reader.py`'s `filter_out_formula_rows` to exclude formula **cells** individually rather than dropping the whole row — this bug currently discards 100% of line items on realistic templates with a computed second-currency column
- [x] 1.3 Delete `mapping_service.py`'s rule/embedding matching apparatus (`rule_based_suggestion`, `suggest_mapping`, `suggest_semantic_mapping`, `_match_unknown_fields`, the embedding/Redis caching helpers) — superseded by AI-first extraction
- [x] 1.4 Delete `mapping_routes.py`'s `/suggest`, `/mappings`, `/mappings/by-ngo/{ngo_id}`, `/fields`, `/fields/bulk`, `/fields/{template_id}`, and debug `/ping` endpoints; delete `mapping_crud.py`'s field-mapping CRUD functions; delete `mapping_schema.py`'s field/mapping/suggestion schemas; keep and adapt only the `DonorTemplateModel`-related CRUD
- [x] 1.5 Delete `DonorFieldModel`, `NgoMappingModel`, `SemanticFieldMappingModel` (`mapping.py`) and `UploadedTemplateModel`, `TemplateToBudgetMappingModel` (`budget_templates.py`); delete `test_mapping_routes_wiring.py` (tests the deleted routes)
- [x] 1.6 Write a migration dropping the now-dead `donor_fields`, `ngo_mappings`, `semantic_field_mappings`, `uploaded_templates`, `template_budget_mappings` tables — re-verify they're empty in all environments immediately before the drop runs
- [x] 1.7 Remove `sentence-transformers` and `torch` from budget-service `requirements.txt`; remove `redis` too if nothing else in the service uses it
- [x] 1.8 Extend `DonorTemplateModel` with `fingerprint` (indexed string), `detected_structure` (JSONB), and `version` (int, default 1) via migration
- [x] 1.9 Store the uploaded `.xlsx` via the existing cloud-agnostic storage capability (not local disk)
- [x] 1.10 Implement the extraction pipeline: clean the sheet via the fixed `spreadsheet_reader.py`, compute a structure fingerprint, look up any `DonorTemplateModel` with a matching fingerprint (global lookup, not scoped to the uploading organization) — if found, extract lines directly from its `detected_structure`; otherwise call a new AI-service extraction capability
- [x] 1.11 Add the AI-service extraction capability: a structured-output PydanticAI call (following `parse_service.py`'s pattern) that returns category/description/amount/currency per line from a cleaned sheet dump, BYOK-preferred with a GrantFlow-funded cheap-model fallback when no provider key is configured
- [x] 1.12 Add cost-tagged audit logging for every AI extraction call (funding source, tokens, cost, duration), matching `parse_service.py`'s `write_audit_log` pattern; add a per-organization rate limit on GrantFlow-funded calls
- [x] 1.13 Route unresolved/low-confidence extraction results into `extra_fields` on the produced line rather than dropping them
- [x] 1.14 Implement `POST /budgets/import-excel`: accept a multipart `.xlsx` upload, run the pipeline above, call `create_budget_with_lines_service` with `status: ai_draft`, setting `BudgetModel.donor_template_id` when a template was matched
- [x] 1.15 Add tests: valid-file happy path, invalid/corrupt file rejection, total-row exclusion, unresolved-data `extra_fields` passthrough, fingerprint match skips AI, no-provider-key falls back to the platform-funded model, platform-funded call failure fails gracefully, rate limit enforced
- [ ] 1.16 Run budget and ai service tests/lint clean; PR merged

## 2. Save-as-template flow — depends on 1

- [x] 2.1 On budget confirmation (existing confirm transition on `PATCH /budgets/{id}`), if the budget originated from an Excel import with no matched template (a fresh AI extraction) and its lines were not edited since creation, surface an optional "save as reusable template" action
- [x] 2.2 On save, create a new `DonorTemplateModel` (with the computed fingerprint and `detected_structure`, user-provided name) and set the originating budget's `donor_template_id` if not already set
- [x] 2.3 Add tests: the save option only appears for unmatched, unedited, Excel-originated `ai_draft` budgets; saving creates a reusable template; a subsequent upload with the same fingerprint (by the same or a different organization) then skips AI extraction
- [ ] 2.4 Run budget service tests/lint clean; PR merged

## 3. Gateway wiring and frontend upload entry point — depends on 1, 2

Note: 3.2/3.3 (upload entry point) and 3.5 (error handling) were re-targeted to chat service's `/chat/import-excel` in Group 4.7 on 2026-08-19 — the UI itself (drop box, visible to every user) is unchanged.

- [x] 3.1 ~~Add the `/budgets/import-excel` route~~ — superseded, see 4.6 (budget's `prepare-import` route replaces it; `/chat/import-excel` should already be covered by the existing `/chat/*` prefix)
- [x] 3.2 Add an "Import from Excel" upload entry point (button + file picker) to the budget list view
- [x] 3.3 On successful upload, navigate to the created `ai_draft` budget's single-budget view so the user lands on the existing confirm/edit review flow
- [x] 3.4 Add the optional "save as reusable template" prompt UI on confirm, wired to group 2's backend action
- [x] 3.5 Handle and surface upload/parse errors (invalid file, parse failure, rate limit) in the UI without a partial or broken navigation
- [ ] 3.6 Manually verify end-to-end with a handful of real-shaped org spreadsheets in staging before enabling for all orgs
- [ ] 3.7 Run frontend and budget service tests/lint clean; PR merged

## 4. Move Excel-import orchestration into chat service — depends on 1, 2; supersedes 1.10, 1.11, 1.14, 3.1, 3.2, 3.3, 3.5

- [x] 4.1 Add `donor_template_id: int | None` (matches `DonorTemplateModel.id`'s actual `Integer` type, not `UUID` as originally drafted here) plus `excel_import_fingerprint`/`excel_import_structure`/`excel_import_lines_locked_count` to `CreateBudgetWithLinesRequest` (`shared/schemas/budget_with_lines_schema.py`) and thread them through `create_budget_with_lines_service`/`POST /budgets/with-lines`, so a budget created via the new tool can still record its source-template provenance and save-as-template eligibility
- [x] 4.2 Extract budget's existing cleaning/fingerprint-matching logic (currently inside `excel_import_service.py`'s monolithic flow) into a new `POST /budgets/excel/prepare-import` endpoint: accepts the raw `.xlsx`, stores it via `storage_client`, cleans it via `spreadsheet_reader.py`, computes the structure fingerprint, and returns either matched lines (fingerprint hit) or the cleaned row grid + fingerprint (no match) — response shape is the new shared `ExcelPrepareImportResult` (`shared/schemas/excel_import_schema.py`)
- [x] 4.3 Delete `POST /budgets/import-excel` and the parts of `excel_import_service.py` that called `ai` service's extraction endpoint and `create_budget_with_lines_service` directly; keep only the prepare-import logic from 4.2. Also removed budget's now-fully-unused `AiClient`/`app.state.http_client` lifespan wiring (`main.py`) — nothing referenced them once the direct ai call was gone
- [x] 4.4 Add a `create_budget_with_lines` tool to chat's tool registry (`budget_tool_registry.py` + `mcp_bridge.py`'s route maps + `tools.py`'s `TOOL_PARAM_MODELS`), wrapping budget's `POST /budgets/with-lines`. Note: FastMCP truncates the pre-transform tool name to 56 chars *before* the rename transform's lookup — the transform key had to be the truncated operationId, not the raw one, or the rename silently never applied
- [x] 4.5 Add `POST /chat/import-excel` to chat service (`chat_routes.py` + new `app/services/import_excel.py`): a non-conversational route (multipart upload, not SSE) that forwards the file to budget's `/budgets/excel/prepare-import`, calls `ai`'s existing `/ai/extract-budget-excel` when no fingerprint match is returned, and calls the new `create_budget_with_lines` tool to persist — forwarding the caller's bearer token to both downstream calls, matching the existing tool-dispatch pattern
- [x] 4.6 Verified (no edits needed): `/budgets/excel/prepare-import` and `/chat/import-excel` both already fall under the existing prefix location/handle blocks (`/api/v1/budgets/`, `/api/v1/chat/`) in `nginx-dev.conf`, `nginx.conf`, and the `Caddyfile` — all three route by prefix, not by an explicit per-path allowlist
- [x] 4.7 Update the frontend's `importBudgetFromExcel` (`budgetApi.ts`) to POST to chat service's `/chat/import-excel` instead of budget service's (now-deleted) `/budgets/import-excel`; UI itself (`ImportExcelModal.tsx` drop box, visibility to all users) is unchanged
- [x] 4.8 Rewrote the Group 1 extraction-pipeline tests that exercised `/budgets/import-excel` end-to-end: `test_excel_import_service.py`/`test_budget_import_excel_route.py`/`test_save_budget_as_template.py` (budget) now cover `prepare_excel_import_service`/`/budgets/excel/prepare-import`; new `test_import_excel.py` (chat) covers the orchestration end-to-end including the fingerprint-match-skips-AI and AI-failure-status-mapping cases from 1.15; `test_budget_tool_registry.py`/`test_mcp_bridge.py` (chat) cover the new tool's dispatch and curated schema. Also fixed two pieces of pre-existing schema drift the refreshed `budget_openapi.json` cache surfaced (unrelated to this feature): `create_budget`/`update_budget`'s tool schemas were missing `donor_total_amount`/`estimated_exchange_rate` from the allowed-extra list, and `update_budget` was leaking three response-only `BudgetUpdate` fields (`confirmed_at`, `estimated_local_cap`, `can_save_as_template`) into its request schema — now hidden in `mcp_bridge.py`
- [ ] 4.9 Run budget, ai, and chat service tests/lint clean; frontend tests/lint clean; PR merged — tests/lint all green (budget 331, ai 87, chat 85, frontend Budgets suite 164 + `tsc --noEmit` clean); PR not yet opened
