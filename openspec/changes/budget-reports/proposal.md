## Why

The budget service tracks planned spend (`Budget` → `BudgetLine` → `BudgetCategory`) but has no way to record *actual* spend against it. Grantees need to submit reports — e.g. against a "£1000 administrative costs" budget line — attaching receipts and payment proofs over the life of the grant, and funders need to review and approve those reports. This is a compliance-facing capability (nonprofit grant reporting), so evidence integrity (locking submitted attachments, tracking who approved what) matters. No file-storage abstraction exists in the repo today, and the project is explicitly cloud-agnostic (Hetzner-only infra, no AWS/GCP/Azure object storage provisioned), so any new storage capability must not hardcode a specific cloud backend.

## What Changes

- Add a `Report` → `ReportLine` → `Attachment` hierarchy inside the existing `services/budget` codebase (no new microservice), mirroring the established `Budget` → `BudgetLine` → `BudgetCategory` conventions (sync SQLAlchemy, `AuditMixin`, thin `shared/schemas` re-exports).
- `Report` carries a status workflow: `draft → submitted → approved/rejected`, with `rejected → draft` allowed to reopen for edits/resubmission.
- Each `ReportLine` targets one specific `BudgetLine`; multiple lines can target the same budget line over time (e.g. several receipts against one cost category).
- Each `ReportLine` can carry multiple file attachments (invoice + payment-proof pairs, multi-page scans).
- Add a new cloud-agnostic file storage abstraction (`shared/storage/`) built on `fsspec`, defaulting to local-disk storage under the existing bind-mounted `uploads/` directory, swappable to real object storage later via config only.
- New API surface for report/report-line CRUD, submit/review status transitions, and multipart file upload/streaming download — all behind existing auth (`get_validated_user`).
- Enforce upload limits in this first version: 15MB max size, content-type allowlist (PDF, JPEG, PNG, HEIC).
- Enforce authorization: only the user belonging to `budget.funding_customer_id` (the funder) may approve/reject a submitted report.
- Lock `ReportLine`s (and their attachments) as read-only once a report leaves `draft`, until reopened via rejection.

## Capabilities

### New Capabilities
- `budget-reports`: Report submission lifecycle (draft/submitted/approved/rejected) against a Budget, containing report lines that reference specific budget lines, with funder-only review/approval authorization and lock-on-submit semantics.
- `budget-report-attachments`: Multi-attachment file upload/download/delete per report line, including upload validation (size/content-type limits) and streaming retrieval behind authenticated access.
- `cloud-agnostic-storage`: A reusable `shared/storage/` abstraction over `fsspec` providing save/open/delete/exists operations against a config-selected backend (local filesystem by default), with no business logic tied to a specific cloud provider.

### Modified Capabilities
- None. `Budget`/`BudgetLine` gain a new relationship (`Budget.reports`) but no existing requirement/behavior changes.

## Impact

- **New code**: `services/budget/app/models/report.py`, new `app/crud/`, `app/services/`, `app/api/` files for reports/report-lines/attachments; `shared/storage/` module; new Pydantic schemas in `shared/schemas/`.
- **Modified code**: `services/budget/app/models/budget.py` (add `reports` relationship), `app/models/__init__.py`, `app/schemas/__init__.py`, `main.py` (router registration), `services/budget/app/core/config.py` and all three `.env.budget.*` files (new `STORAGE_BACKEND_URL` setting), `services/budget/requirements.txt` (promote `fsspec` from transitive to direct dependency).
- **Database**: one new Alembic migration adding `reports`, `report_lines`, `attachments` tables to the budget service's database.
- **Infra**: no docker-compose changes required (reuses the existing `uploads/` bind mount); flags the `uploads/` directory's lack of backup coverage as an out-of-scope follow-up now that it will hold compliance-relevant files.
- **Out of scope / explicit fast-follows**: budget-line overspend validation (no enforcement that report-line totals stay within a budget line's planned amount), blob/DB two-phase-commit consistency on delete, backup coverage for the uploads directory.
