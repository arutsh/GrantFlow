## Why

The budget service tracks planned spend (`Budget` → `BudgetLine` → `BudgetCategory`) but has no way to record *actual* spend against it. Grantees need to submit reports — e.g. against a "£1000 administrative costs" budget line — attaching receipts and payment proofs over the life of the grant, and funders need to review and approve those reports. This is a compliance-facing capability (nonprofit grant reporting), so evidence integrity (locking submitted attachments, tracking who approved what) matters. No file-storage abstraction exists in the repo today, and the project is explicitly cloud-agnostic (Hetzner-only infra, no AWS/GCP/Azure object storage provisioned), so any new storage capability must not hardcode a specific cloud backend.

Real donor budget templates also reveal that reported amounts routinely need two currencies (the grantee's local spending currency and the specific contract's wire-transfer currency), converted at whatever rate each real bank transaction actually used — not one project-wide FX rate, which grantees have historically had to fudge by hand to make their own summary sheets balance. And real funding is often multi-hop (a donor can itself be a sub-grantee of another, upstream donor), so a report's evidence chain and its currencies need to compose across hops without the system inventing numbers on anyone's behalf.

## What Changes

- Add a `Report` → `ReportLine` → `Attachment` hierarchy inside the existing `services/budget` codebase (no new microservice), mirroring the established `Budget` → `BudgetLine` → `BudgetCategory` conventions (sync SQLAlchemy, `AuditMixin`, thin `shared/schemas` re-exports).
- `Report` carries a status workflow: `draft → submitted → approved/rejected`, with `rejected → draft` allowed to reopen for edits/resubmission.
- Report creation is gated on `Budget.status == confirmed` and a required, non-overlapping reporting period (`period_start`/`period_end`, defaulting to the budget's full span when not specified). Multiple reports can coexist per budget as long as their periods don't overlap, regardless of individual report status — supporting periodic (e.g. interim/final) reporting without blocking a grantee from drafting the next period while a prior one is still under review.
- Each `ReportLine` targets one specific `BudgetLine`; multiple lines can target the same budget line over time (e.g. several receipts against one cost category).
- Each `ReportLine` can carry multiple file attachments (invoice + payment-proof pairs, multi-page scans).
- Add a new cloud-agnostic file storage abstraction (`shared/storage/`) built on `boto3` against an S3-compatible backend (self-hosted MinIO for local dev, Cloudflare R2 in production — bucket `open-grantflow-reports` already provisioned), swappable to any other S3-compatible provider later via config only, with `boto3` calls confined entirely to the abstraction layer.
- New API surface for report/report-line CRUD, submit/review status transitions, and multipart file upload/streaming download — all behind existing auth (`get_validated_user`).
- Enforce upload limits in this first version: 15MB max size, content-type allowlist (PDF, JPEG, PNG, HEIC).
- Enforce authorization: only the user belonging to `budget.funding_customer_id` (the funder) may approve/reject a submitted report; when a budget has no `funding_customer_id` set (no in-system funder — e.g. a grantee tracking their own budget for later export to a donor template), the budget owner may self-review instead.
- Lock `ReportLine`s (and their attachments) as read-only once a report leaves `draft`, until reopened via rejection.
- Add a currency ledger (`FundingReceiptModel`, `CurrencyConversionModel`) so a grantee's donor-currency receipts and their irregular, real-rate conversions to local currency are tracked as auditable events, with expenses drawn down against them FIFO (allowed to go negative when spend precedes the next conversion).
- Add `Budget.actual_currency` (the wire-transfer currency for that specific contract, independent of the existing per-budget `local_currency`) and `Budget.parent_budget_id` (optional self-reference for when a donor is itself a sub-grantee of another, upstream donor — used to derive "donor's currency" without storing it redundantly).
- Add `ReportLine.source_report_id` (optional FK to another `Report`) so an intermediate donor can manually link a downstream grantee's approved report as backing evidence inside their own upstream report — no automatic cross-hop aggregation or conversion.

## Capabilities

### New Capabilities
- `budget-reports`: Report submission lifecycle (draft/submitted/approved/rejected) against a Budget, containing report lines that reference specific budget lines, with funder-only review/approval authorization and lock-on-submit semantics.
- `budget-report-attachments`: Multi-attachment file upload/download/delete per report line, including upload validation (size/content-type limits) and streaming retrieval behind authenticated access.
- `cloud-agnostic-storage`: A reusable `shared/storage/` abstraction over `boto3` providing save/open/delete/exists operations against any S3-compatible backend (MinIO for local dev, Cloudflare R2 in production), with `boto3` confined to the abstraction layer and no business logic tied to a specific provider.
- `budget-currency-ledger`: Auditable tracking of donor-currency receipts and their real, per-transaction conversion to local currency, with FIFO consumption by report-line expenses — replacing any notion of a single project-wide FX rate.

### Modified Capabilities
- `Budget`/`BudgetLine` gain a new relationship (`Budget.reports`), plus new fields `Budget.actual_currency` and `Budget.parent_budget_id` (both additive, no existing requirement/behavior changes to current fields).

## Impact

- **New code**: `services/budget/app/models/report.py`, new `app/crud/`, `app/services/`, `app/api/` files for reports/report-lines/attachments; `shared/storage/` module; new Pydantic schemas in `shared/schemas/`; new models for `FundingReceiptModel`/`CurrencyConversionModel` and their CRUD/service/API layers.
- **Modified code**: `services/budget/app/models/budget.py` (add `reports` relationship, `actual_currency`, `parent_budget_id`, `start_date`), `app/models/__init__.py`, `app/schemas/__init__.py`, `main.py` (router registration), `services/budget/app/core/config.py` and all three `.env.budget.*` files (new `STORAGE_ENDPOINT_URL`/`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`/`STORAGE_BUCKET_NAME` settings), `services/budget/requirements.txt` (add `boto3` as a new direct dependency).
- **Database**: new Alembic migration(s) adding `reports`, `report_lines`, `attachments`, `funding_receipts`, `currency_conversions` tables, plus new columns on `budgets` (`actual_currency`, `parent_budget_id`, `start_date`) and `report_lines` (`source_report_id`).
- **Infra**: `docker-compose.yml` gains a new `minio` service for local development; production uploads go to the already-provisioned Cloudflare R2 bucket `open-grantflow-reports` (free tier — flagged as a follow-up if usage approaches free-tier caps).
- **Out of scope / explicit fast-follows**: budget-line overspend validation (no enforcement that report-line totals stay within a budget line's planned amount), blob/DB two-phase-commit consistency on delete, backup coverage for the uploads directory, automatic multi-hop rollup/conversion across a funding chain, and a possible second FIFO ledger for an intermediate donor's own upstream conversion (open question — see `design.md`).
