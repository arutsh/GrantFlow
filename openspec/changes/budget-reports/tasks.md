Workflow rule: **one group = one GitHub ticket = one PR, merged before the next group starts.** Branch names are fixed per ticket. Every PR: `flake8 --max-line-length=100` clean; commits/pushes only with explicit user approval.

## 1. Budget currency & reporting-period fields — ticket #144 (`Budget/Issue-144/currency-fields`)

- [x] 1.1 Add `actual_currency` (nullable `String(3)`) and `start_date` (nullable `Date`) columns to `BudgetModel` in `app/models/budget.py`
- [x] 1.2 Write Alembic migration `000004_add_budget_currency_fields.py` (down_revision `000003` — chain drifted, see note below) adding both columns, with matching `downgrade()`
- [x] 1.3 Run `alembic upgrade head` / `alembic downgrade -1` locally to verify the migration applies and reverses cleanly
- [x] 1.4 Extend `shared/schemas/budget_schema.py` with `actual_currency` and `start_date` on the relevant `Budget*` schemas
- [x] 1.6 Enforce `start_date` is set before a budget's status can be changed to `confirmed` (in `update_budget_service`); reject the update otherwise
- [x] 1.7 Add `services/budget/tests/test_budget_currency_fields.py`: column round-trip, confirming a budget without `start_date` cannot transition to `confirmed`
- [x] 1.8 Run `pytest services/budget` and `flake8 --max-line-length=100`; PR merged

**Dropped from this ticket (2026-07-24):** `Budget.parent_budget_id` and `resolve_donor_currency(budget)` (originally 1.1/1.4/1.5). Audited against tickets 2–5 and found nothing in the current `budget-reports` scope ever consumes them — the donor-currency-chain display they exist for (proposal.md's "Rollup/spreadsheet-style summary reporting") is explicitly out of scope for #144–148. Re-add as their own ticket when that feature is actually scoped, per the project's no-speculative-fields convention. See design.md's "Donor's own reporting currency..." decision, now marked deferred.

> Note: `000002` was already the head when this ticket's design.md was written, but `000003_add_budget_total_amount` landed first from unrelated work. This migration chains off the real head (`000003`) and is numbered `000004`. Tickets 3–5 below reference `000004`/`000005`/`000006` — re-check the actual head before writing those; they'll likely need to shift to `000005`/`000006`/`000007`.

## 2. Cloud-agnostic (S3-compatible) storage abstraction — ticket #145 (`Shared/Issue-145/storage-abstraction`)

- [x] 2.1 Add `shared/storage/__init__.py`, abstract `StorageService` (`save`, `open_stream`, `delete`, `exists`) in `shared/storage/storage_service.py`, and concrete `S3StorageService(StorageService)` wrapping a `boto3` S3 client in `shared/storage/s3_storage_service.py` — the only file in the repo permitted to import `boto3` (split from the abstract interface so a future non-S3 backend can be added as a sibling subclass); lazily creates the configured bucket on first `save()` if it doesn't already exist
- [x] 2.2 Add `shared/storage/config.py` reading `STORAGE_ENDPOINT_URL`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET_NAME`
- [x] 2.3 Add `boto3` as a new direct, pinned dependency in `services/budget/requirements.txt`
- [x] 2.4 Add `STORAGE_ENDPOINT_URL`/`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`/`STORAGE_BUCKET_NAME` to `services/budget/app/core/config.py` `Settings` and to all three `.env.budget.*` files (dev values point at the local MinIO container; prod values point at the `open-grantflow-reports` Cloudflare R2 bucket)
- [x] 2.5 Add a `minio` service to `docker-compose.yml` (default dev credentials, a bind-mounted data volume) for local development
- [x] 2.6 Add `services/budget/app/services/storage_client.py` — module-level `StorageService` instance for the budget service to import
- [x] 2.7 Write `services/budget/tests/test_storage_service.py` — round-trip test for save/open_stream/delete/exists against the local MinIO container (skips gracefully if MinIO isn't reachable; verified passing against a live local MinIO container)
- [x] 2.8 Add a lint/test guard (e.g. a grep-based test) confirming `boto3` is imported only inside `shared/storage/s3_storage_service.py` — `shared/tests/test_storage_boto3_confinement.py`
- [x] 2.9 Run `pytest services/budget` and `flake8 --max-line-length=100`; PR merged

## 3. Report submission lifecycle — ticket #146 (`Budget/Issue-146/report-submission-lifecycle`)

- [ ] 3.1 Create `services/budget/app/models/report.py` with `ReportStatus` enum and `ReportModel`, `ReportLineModel`, mirroring `budget.py`'s `AuditMixin`/GUID style
- [ ] 3.2 Add `reports` relationship to `BudgetModel` in `services/budget/app/models/budget.py`
- [ ] 3.3 Register the new models in `services/budget/app/models/__init__.py`
- [ ] 3.4 Write Alembic migration `000004_add_reports_report_lines.py` (down_revision `000003`) creating `reports`, `report_lines`, with matching `downgrade()`
- [ ] 3.5 Run `alembic upgrade head` / `alembic downgrade -1` locally to verify the migration applies and reverses cleanly
- [ ] 3.6 Add `shared/schemas/report_schema.py` (`ReportStatus`, `ReportBase/Create/Update`, `Report`, `ReportWithLines`)
- [ ] 3.7 Add `shared/schemas/report_line_schema.py` (`ReportLineBase/Create/Update`, `ReportLine`)
- [ ] 3.8 Add thin re-export modules in `services/budget/app/schemas/` for both, and update `services/budget/app/schemas/__init__.py`
- [ ] 3.9 Add `services/budget/app/crud/report_crud.py` (create/get/list/update/delete/transition_status)
- [ ] 3.10 Add `services/budget/app/crud/report_line_crud.py` (create/get/list/update/delete)
- [ ] 3.11 Add `services/budget/app/services/report_services.py`: create (rejects unless `budget.status == confirmed`; defaults `period_start`/`period_end` to the budget's full span — `budget.start_date` through `budget.start_date + duration_months` — when not supplied; rejects if the resulting period overlaps any other report already existing for the same budget, regardless of that report's status), get/list/update/delete, `submit_report_service` (draft→submitted), `review_report_service` (submitted→approved/rejected; authorization is the user matching `budget.funding_customer_id` when set, else the budget owner when `funding_customer_id` is `None`), reopen (rejected→draft)
- [ ] 3.12 Add `services/budget/app/services/report_line_services.py`: create/get/list/update/delete, enforcing draft-only lock and same-budget cross-check between `budget_line_id` and the report's budget
- [ ] 3.13 Add `services/budget/app/api/report_routes.py`: CRUD + `POST /{id}/submit` + `POST /{id}/review`
- [ ] 3.14 Add `services/budget/app/api/report_line_routes.py`: CRUD + `GET /by-report/{report_id}`
- [ ] 3.15 Register both routers in `services/budget/main.py`
- [ ] 3.16 Add `services/budget/tests/factories/report.py`: `ReportFactory`, `ReportLineFactory`
- [ ] 3.17 Add `services/budget/tests/test_report_routes.py`: CRUD, permission checks (owner/funder/neither), report creation rejected against a non-`confirmed` budget, report creation defaults period to the budget's full span when omitted, report creation rejected on period overlap (including against a `rejected` report) and allowed on non-overlapping periods regardless of status, submit transition, review transition (funder-only enforcement when `funding_customer_id` is set, owner self-review when it is not)
- [ ] 3.18 Add `services/budget/tests/test_report_line_routes.py`: create/update rejected on non-draft report, cross-budget `budget_line_id` rejected
- [ ] 3.19 Run `pytest services/budget` and `flake8 --max-line-length=100`; PR merged

## 4. Report attachments — ticket #147 (`Budget/Issue-147/report-attachments`)

- [ ] 4.1 Add `AttachmentModel` to `services/budget/app/models/report.py`, FK to `report_lines`
- [ ] 4.2 Register the new model in `services/budget/app/models/__init__.py`
- [ ] 4.3 Write Alembic migration `000005_add_attachments.py` (down_revision `000004`) creating `attachments`, with matching `downgrade()`
- [ ] 4.4 Run `alembic upgrade head` / `alembic downgrade -1` locally to verify the migration applies and reverses cleanly
- [ ] 4.5 Add `shared/schemas/attachment_schema.py` (`AttachmentBase`, `Attachment`)
- [ ] 4.6 Add a thin re-export module in `services/budget/app/schemas/`, and update `services/budget/app/schemas/__init__.py`
- [ ] 4.7 Add `services/budget/app/crud/attachment_crud.py` (create/get/list/delete)
- [ ] 4.8 Add `services/budget/app/services/attachment_services.py`: `upload_attachment_service` (size/content-type validation, draft-only lock, calls `storage_client.save`), `download_attachment_service` (auth chain + `storage_client.open_stream`), `delete_attachment_service` (draft-only lock, blob delete then row delete)
- [ ] 4.9 Add `services/budget/app/api/attachment_routes.py`: multipart `POST /`, `GET /by-report-line/{report_line_id}`, streaming `GET /{id}/content`, `DELETE /{id}/`
- [ ] 4.10 Register the router in `services/budget/main.py`
- [ ] 4.11 Add `services/budget/tests/factories/attachment.py`: `AttachmentFactory`
- [ ] 4.12 Add `services/budget/tests/test_attachment_routes.py`: upload happy path, oversized/disallowed-type rejection, draft-only lock, download permission checks
- [ ] 4.13 Manually exercise the full flow against the running dev stack: create budget + budget line → create draft report → add report line → upload receipt → download it back → submit → confirm line/attachment edits now rejected → attempt review as owner (rejected) → review as funder (approve or reject) → if rejected, reopen to draft and confirm edits are allowed again
- [ ] 4.14 Run `pytest services/budget` and `flake8 --max-line-length=100`; PR merged

## 5. Currency ledger + cross-hop rollup — ticket #148 (`Budget/Issue-148/currency-ledger`)

- [ ] 5.1 Create `services/budget/app/models/currency_ledger.py` with `FundingReceiptModel`, `CurrencyConversionModel`, and `ReportLineConversionAllocationModel` (the FIFO lot-split join: `report_line_id`, `conversion_id`, `amount_allocated`), mirroring `AuditMixin`/GUID style
- [ ] 5.2 Add `source_report_id` (nullable FK to `reports.id`) to `ReportLineModel` in `app/models/report.py`
- [ ] 5.3 Register the new models in `app/models/__init__.py`
- [ ] 5.4 Write Alembic migration `000006_add_currency_ledger.py` (down_revision `000005`) adding `funding_receipts`, `currency_conversions`, `report_line_conversion_allocations`, plus the `source_report_id` column on `report_lines`, with matching `downgrade()`
- [ ] 5.5 Run `alembic upgrade head` / `alembic downgrade -1` locally to verify this migration applies and reverses cleanly
- [ ] 5.6 Add `shared/schemas/currency_ledger_schema.py` (`FundingReceiptBase/Create`, `FundingReceipt`, `CurrencyConversionBase/Create`, `CurrencyConversion`)
- [ ] 5.7 Extend `shared/schemas/report_line_schema.py` with optional `source_report_id`
- [ ] 5.8 Add thin re-export modules in `services/budget/app/schemas/` for the new currency-ledger schemas, and update `services/budget/app/schemas/__init__.py`
- [ ] 5.9 Add `services/budget/app/crud/funding_receipt_crud.py` (create/get/list)
- [ ] 5.10 Add `services/budget/app/crud/currency_conversion_crud.py` (create/get/list, plus a query returning unconsumed conversion lots ordered oldest-first for FIFO)
- [ ] 5.11 Add `services/budget/app/services/currency_ledger_services.py`: `record_receipt_service`, `record_conversion_service`, and `allocate_fifo_service(report_line)` — walks unconsumed conversion lots oldest-first, creates `ReportLineConversionAllocation` rows (splitting across lots when one expense straddles more than one), allows the running balance to go negative without blocking or warning
- [ ] 5.12 Wire `report_line_services.py`'s create path (from ticket #146) to call `allocate_fifo_service` so every new expense line is automatically allocated against the ledger
- [ ] 5.13 Add `services/budget/app/api/funding_receipt_routes.py`: CRUD scoped to the budget owner
- [ ] 5.14 Add `services/budget/app/api/currency_conversion_routes.py`: CRUD scoped to the budget owner
- [ ] 5.15 Register both new routers in `services/budget/main.py`
- [ ] 5.16 Add `services/budget/tests/factories/currency_ledger.py`: `FundingReceiptFactory`, `CurrencyConversionFactory`
- [ ] 5.17 Add `services/budget/tests/test_currency_ledger.py`: FIFO allocation against a single lot, allocation split across multiple lots, negative-balance case that trues up on the next conversion, per-currency (never blended) balance reporting
- [ ] 5.18 Add a manual-rollup traceability test: create a `ReportLine` with `source_report_id` pointing at another budget's approved report; confirm no automatic amount or currency computation occurs
- [ ] 5.19 Manually exercise the currency ledger: record a funding receipt → record a partial conversion → add an expense report line exceeding the converted balance (confirm negative balance is allowed, not blocked) → record a second conversion → confirm the balance trues up
- [ ] 5.20 Run `pytest services/budget` and `flake8 --max-line-length=100`; PR merged
