## Why

The `services/budget` backend now (or imminently will, per a parallel in-flight session) support the full report submission lifecycle — `Budget.status == confirmed` gating, `Report`/`ReportLine`/`Attachment` CRUD, submit/review/reopen transitions, and file upload/download (tickets #144–#147) — but none of it is reachable from the frontend. Grantees have no way to confirm a budget (the precondition for reporting), draft a report, attach receipts, or submit for review; funders have no way to see or act on submitted reports. The `DonorDashboard`'s "View Reports" button already exists as a disabled `Coming soon` placeholder, signalling this gap was anticipated but not built. This change closes it entirely on the frontend, plus the small amount of gateway (nginx) wiring the new backend routes need to be reachable at all.

## What Changes

- Add a **budget confirmation** action on the single-budget view: a grantee sets `start_date` and transitions a `draft`/`ai_draft` budget to `confirmed` (the backend's existing precondition, enforced since ticket #144), unlocking report creation for that budget.
- Add a **Reports** section to the single-budget view: list existing reports (period, status), create a new report (optionally overriding the default full-span period), and open a report detail view.
- Add a **report detail view**: shows report metadata and status, lists report lines (each tied to one budget line), supports adding/editing/deleting lines while the report is `draft`, and exposes **Submit** (draft → submitted), **Review** (submitted → approved/rejected, funder/owner-fallback only), and **Reopen** (rejected → draft) actions gated by the current user's role and the report's status, mirroring the backend's authorization rules.
- Add **attachment upload/list/download/delete** on each report line, enforcing the same 15MB / PDF-JPEG-PNG-HEIC constraints client-side (as a UX nicety; the backend remains the source of truth) and disabling upload/delete once the parent report leaves `draft`.
- Wire the `DonorDashboard`'s existing disabled "View Reports" button through to the same report list/detail views, scoped to the funder's read/review access.
- Extend `frontend-typescript/src/pages/Budgets/types/budget.ts` with the new `Report`, `ReportLine`, `Attachment` types and the `Budget.start_date`/`Budget.actual_currency` fields already present on the backend model.
- Add nginx `location` blocks (both `nginx/nginx.conf` and `nginx/nginx-dev.conf`) proxying `/api/v1/reports/`, `/api/v1/report-lines/`, and `/api/v1/attachments/` to the budget service — this backend surface exists but is not yet reachable through the gateway.

## Capabilities

### New Capabilities
- `budget-confirmation-ui`: frontend action to set a budget's `start_date` and transition it from `draft`/`ai_draft` to `confirmed`, gating report creation on the confirmed state.
- `budget-report-ui`: frontend report/report-line lifecycle — list, create, view, edit, submit, review (approve/reject), and reopen reports against a confirmed budget, with role-and-status-gated actions matching the backend's authorization rules.
- `budget-report-attachment-ui`: frontend upload/list/download/delete of file attachments on report lines, with client-side size/content-type validation and draft-only-lock affordances.

### Modified Capabilities
(none — no existing frontend spec covers budget CRUD or the donor dashboard today, so nothing here changes a previously-specified requirement)

## Impact

- **New code**: `frontend-typescript/src/api/reportApi.ts` (reports/report-lines/attachments API calls), `frontend-typescript/src/pages/Budgets/components/BudgetConfirmAction.tsx`, `.../ReportsList.tsx`, `.../ReportDetail.tsx`, `.../ReportLineRow.tsx`, `.../AttachmentUpload.tsx`, a new route (e.g. `/budgets/:id/reports/:reportId`) registered in `App.tsx`.
- **Modified code**: `frontend-typescript/src/pages/Budgets/types/budget.ts` (new fields/types), `SingleBudgetView.tsx` (confirmation action + Reports section), `DonorDashboard.tsx` (wire up "View Reports"), `nginx/nginx.conf` and `nginx/nginx-dev.conf` (new proxy routes).
- **Out of scope**: the currency ledger UI (`FundingReceipt`/`CurrencyConversion`/FIFO balances) — backend ticket #148 for this hasn't started yet; revisit once it lands. Cross-hop rollup UI (`ReportLine.source_report_id`) is likewise unscoped, matching the backend proposal's own deferral. Presigned/direct-to-storage upload stays a backend-side fast-follow, not a frontend concern yet.
