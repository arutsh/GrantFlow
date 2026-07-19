## 1. Storage abstraction (`shared/storage/`)

- [ ] 1.1 Add `shared/storage/__init__.py`, `shared/storage/storage_service.py` implementing `StorageService` (`save`, `open_stream`, `delete`, `exists`) wrapping `fsspec.core.url_to_fs`
- [ ] 1.2 Add `shared/storage/config.py` reading `STORAGE_BACKEND_URL` (default `file:///app/uploads/reports`)
- [ ] 1.3 Promote `fsspec` from transitive to direct, pinned dependency in `services/budget/requirements.txt`
- [ ] 1.4 Add `STORAGE_BACKEND_URL` to `services/budget/app/core/config.py` `Settings` and to all three `.env.budget.*` files
- [ ] 1.5 Add `services/budget/app/services/storage_client.py` — module-level `StorageService` instance for the budget service to import
- [ ] 1.6 Write `services/budget/tests/test_storage_service.py` — real-disk round-trip test (`file://` + pytest `tmp_path`) for save/open_stream/delete/exists

## 2. Data model

- [ ] 2.1 Create `services/budget/app/models/report.py` with `ReportStatus` enum and `ReportModel`, `ReportLineModel`, `AttachmentModel`, mirroring `budget.py`'s `AuditMixin`/GUID style
- [ ] 2.2 Add `reports` relationship to `BudgetModel` in `services/budget/app/models/budget.py`
- [ ] 2.3 Register new models in `services/budget/app/models/__init__.py`
- [ ] 2.4 Write Alembic migration `000003_add_reports_report_lines_attachments.py` (down_revision `000002`) creating `reports`, `report_lines`, `attachments`, with matching `downgrade()`
- [ ] 2.5 Run `alembic upgrade head` / `alembic downgrade -1` locally to verify the migration applies and reverses cleanly

## 3. Schemas

- [ ] 3.1 Add `shared/schemas/report_schema.py` (`ReportStatus`, `ReportBase/Create/Update`, `Report`, `ReportWithLines`)
- [ ] 3.2 Add `shared/schemas/report_line_schema.py` (`ReportLineBase/Create/Update`, `ReportLine`)
- [ ] 3.3 Add `shared/schemas/attachment_schema.py` (`AttachmentBase`, `Attachment`)
- [ ] 3.4 Add thin re-export modules in `services/budget/app/schemas/` for all three, and update `services/budget/app/schemas/__init__.py`

## 4. CRUD layer

- [ ] 4.1 Add `services/budget/app/crud/report_crud.py` (create/get/list/update/delete/transition_status)
- [ ] 4.2 Add `services/budget/app/crud/report_line_crud.py` (create/get/list/update/delete)
- [ ] 4.3 Add `services/budget/app/crud/attachment_crud.py` (create/get/list/delete)

## 5. Service layer

- [ ] 5.1 Add `services/budget/app/services/report_services.py`: create/get/list/update/delete, `submit_report_service` (draft→submitted), `review_report_service` (submitted→approved/rejected, enforces funder-only authorization), reopen (rejected→draft)
- [ ] 5.2 Add `services/budget/app/services/report_line_services.py`: create/get/list/update/delete, enforcing draft-only lock and same-budget cross-check between `budget_line_id` and the report's budget
- [ ] 5.3 Add `services/budget/app/services/attachment_services.py`: `upload_attachment_service` (size/content-type validation, draft-only lock, calls `storage_client.save`), `download_attachment_service` (auth chain + `storage_client.open_stream`), `delete_attachment_service` (draft-only lock, blob delete then row delete)

## 6. API routes

- [ ] 6.1 Add `services/budget/app/api/report_routes.py`: CRUD + `POST /{id}/submit` + `POST /{id}/review`
- [ ] 6.2 Add `services/budget/app/api/report_line_routes.py`: CRUD + `GET /by-report/{report_id}`
- [ ] 6.3 Add `services/budget/app/api/attachment_routes.py`: multipart `POST /`, `GET /by-report-line/{report_line_id}`, streaming `GET /{id}/content`, `DELETE /{id}/`
- [ ] 6.4 Register all three routers in `services/budget/main.py`

## 7. Tests

- [ ] 7.1 Add `services/budget/tests/factories/report.py`: `ReportFactory`, `ReportLineFactory`, `AttachmentFactory`
- [ ] 7.2 Add `services/budget/tests/test_report_routes.py`: CRUD, permission checks (owner/funder/neither), submit transition, review transition (funder-only enforcement)
- [ ] 7.3 Add `services/budget/tests/test_report_line_routes.py`: create/update rejected on non-draft report, cross-budget `budget_line_id` rejected
- [ ] 7.4 Add `services/budget/tests/test_attachment_routes.py`: upload happy path, oversized/disallowed-type rejection, draft-only lock, download permission checks

## 8. End-to-end verification

- [ ] 8.1 Run full budget-service test suite (`pytest services/budget`) and confirm no regressions
- [ ] 8.2 Manually exercise the flow against the running dev stack: create budget + budget line → create draft report → add report line → upload receipt → download it back → submit → confirm line/attachment edits now rejected → attempt review as owner (rejected) → review as funder (approve or reject) → if rejected, reopen to draft and confirm edits are allowed again
- [ ] 8.3 Run `flake8 --max-line-length=100` over all new/changed files
