Workflow rule: **one group = one GitHub ticket = one PR, merged before the next group starts.** Tickets are already created (see each group's heading); branch per ticket as `Frontend/Issue-<n>/<short-desc>`. Do not start a group until the previous one's PR is merged. Every PR: `npm run lint` (and any equivalent type-check) clean; commits/pushes only with explicit user approval.

Exception to strict ordering: **group 7 (currency ledger, #165) is externally blocked** on a concurrent session's backend ticket #148 (`Budget/Issue-148/currency-ledger`, in the `budget-reports` change), which is specced but not yet implemented. It only depends on group 1 (#159), not on groups 2–6, so it can be picked up whenever #148 lands — including in parallel with or ahead of groups 2–6 — without stalling the rest of this change on someone else's backend timeline.

## 1. Foundation — gateway wiring, shared types, API layer — ticket #159 (`Frontend/Issue-159/budget-report-foundation`)

- [x] 1.1 Add `location /api/v1/reports/`, `/api/v1/report-lines/`, `/api/v1/attachments/` blocks to `nginx/nginx-dev.conf`, mirroring the existing `/budgets/`/`/budget-lines/` blocks (simple `proxy_pass` to the `budget` upstream)
- [x] 1.2 Add the same three `location` blocks to `nginx/nginx.conf`, mirroring its `rewrite ... break` + variable-`proxy_pass` pattern used for `/budgets/`/`/budget-lines/`
- [x] 1.3 Manually verify (once the backend branch with #146/#147 is merged) that `GET /api/v1/reports/by-budget/{id}` and `GET /api/v1/attachments/by-report-line/{id}` reach the budget service through the dev nginx container — confirmed via `curl` through `localhost:8082`: `reports/by-budget`, `report-lines/by-report`, `attachments/by-report-line`, and `attachments/{id}/download-url` all return `401` (reaches the budget service, auth-gated), same as the existing `/budgets/` route
- [x] 1.4 Extend `frontend-typescript/src/pages/Budgets/types/budget.ts`: add `start_date`/`actual_currency` to `Budget`/`BudgetUpdate`/`BudgetPatched`; add `Report`, `ReportLine`, `Attachment`, `ReportStatus` types matching `shared/schemas/report_schema.py`/`report_line_schema.py`/`attachment_schema.py`
- [x] 1.5 Create `frontend-typescript/src/api/reportApi.ts`: `createReport`, `listReportsByBudget`, `getReport`, `updateReport`, `deleteReport`, `submitReport`, `reviewReport`, `reopenReport`
- [x] 1.6 Add report-line calls to `reportApi.ts`: `createReportLine`, `listReportLinesByReport`, `updateReportLine`, `deleteReportLine`
- [x] 1.7 Add attachment calls to `reportApi.ts`: `uploadAttachment` (multipart `FormData`), `listAttachmentsByReportLine`, `downloadAttachment` (blob response, trigger browser download), `deleteAttachment`
- [x] 1.8 Add a small `src/utils/roleAccess.ts` (or extend an existing utils file) with a `getCurrentCustomerId()` helper decoding `customer_id` from the JWT (same `safeDecodeToken` used by `AuthContext`), and `canReviewReport(budget, currentCustomerId)` / `isBudgetOwner(budget, currentCustomerId)` helpers per design.md's UI-only role-gating decision
- [ ] 1.9 Run `npm run lint` / type-check clean; this ticket ships no new UI (types + unused API client + nginx routes only) — verify nothing existing regresses; PR merged — `npm run lint` (89 pre-existing errors, none in the 3 new/changed files), `npx tsc --noEmit` clean, `npx vitest run` 31/31 passing; not yet committed or a PR

## 2. Budget confirmation — ticket #160 (`Frontend/Issue-160/budget-confirmation-ui`) — depends on 1

- [ ] 2.1 Add a "Confirm Budget" inline action (date picker + button) to `BudgetViewHeader.tsx` or `SingleBudgetView.tsx`, visible only when `budget.status` is `draft`/`ai_draft` and the current user owns the budget
- [ ] 2.2 Wire the action to `editBudget(id, { start_date, status: "confirmed" })`, disabled until a date is picked; on success update the budget in the React Query cache (same `setBudget` pattern as `SingleBudgetViewContext`) and show the returned error inline on failure
- [ ] 2.3 Add a component test covering: button hidden when already confirmed, disabled with no date picked, calls `editBudget` with the right payload, shows error on failure
- [ ] 2.4 Run the frontend test suite + `npm run lint` clean; PR merged

## 3. Reports list, creation, and read-only detail — ticket #161 (`Frontend/Issue-161/reports-list-and-detail`) — depends on 1, 2

- [ ] 3.1 Add `frontend-typescript/src/pages/Budgets/components/ReportsList.tsx`: fetches `listReportsByBudget(budget.id)` via React Query, renders each report's name/period/status, empty state with "New Report" when none exist
- [ ] 3.2 Add a "New Report" form/modal (reuse `Modal` from `components/ui`) collecting `name` and optional `period_start`/`period_end`; on submit calls `createReport`, shows the backend's error message inline on rejection (e.g. overlapping period), and on success navigates to the new report's detail route
- [ ] 3.3 Mount `ReportsList` inside `SingleBudgetView.tsx`'s non-edit-mode branch, gated on `budget.status === "confirmed"` or `budget` already having reports
- [ ] 3.4 Add a new route `/budgets/:id/reports/:reportId` in `App.tsx` pointing at a new `ReportDetailView` container
- [ ] 3.5 Add `frontend-typescript/src/pages/Budgets/ReportDetailView.tsx`: reads `:reportId` from the route, fetches the report (`getReport`) and its lines (`listReportLinesByReport`), renders status, period, and a read-only lines table (line CRUD/actions land in ticket 4)
- [ ] 3.6 Add tests: `ReportsList` empty state, list rendering, create-report happy path, overlapping-period error surfaced inline; `ReportDetailView` renders report metadata and lines read-only
- [ ] 3.7 Run the frontend test suite + `npm run lint` clean; PR merged

## 4. Report line CRUD and lifecycle actions — ticket #162 (`Frontend/Issue-162/report-line-lifecycle`) — depends on 3

- [ ] 4.1 Add `ReportLineRow.tsx` (or extend the lines table) supporting add/edit/delete of a line (budget line select, description, amount), enabled only while the report is `draft`
- [ ] 4.2 Wire add/edit/delete to `createReportLine`/`updateReportLine`/`deleteReportLine`, invalidating the report-lines query on success
- [ ] 4.3 Add "Submit" action (visible to the owner when `status === "draft"`) calling `submitReport`, updating the displayed status on success
- [ ] 4.4 Add "Approve"/"Reject" actions (visible when `canReviewReport(budget, currentCustomerId)` is true and `status === "submitted"`), with a review-notes field, calling `reviewReport`
- [ ] 4.5 Add "Reopen" action (visible to the owner when `status === "rejected"`) calling `reopenReport`, re-enabling line edits on success
- [ ] 4.6 Add tests: line CRUD gated by draft status, submit transition, review actions gated by role+status, reopen transition
- [ ] 4.7 Run the frontend test suite + `npm run lint` clean; PR merged

## 5. Attachments — ticket #163 (`Frontend/Issue-163/report-attachments-ui`) — depends on 4

- [ ] 5.1 Add `frontend-typescript/src/pages/Budgets/components/AttachmentUpload.tsx`: file input + upload button per report line, client-side validation (15MB max, PDF/JPEG/PNG/HEIC allowlist) showing an inline error before calling `uploadAttachment`, visible only while the report is `draft`
- [ ] 5.2 List each report line's attachments (filename, size) via `listAttachmentsByReportLine`, with a download control (calls `downloadAttachment`, triggers a browser download using the original filename) and a delete control (calls `deleteAttachment`, visible only while `draft`)
- [ ] 5.3 Integrate `AttachmentUpload`/attachment list into `ReportLineRow.tsx` from ticket 4
- [ ] 5.4 Add tests: oversized/disallowed-type file rejected client-side without a network call, successful upload appends to the list, delete removes from the list, controls hidden once the report leaves `draft`
- [ ] 5.5 Run the frontend test suite + `npm run lint` clean; PR merged

## 6. Donor dashboard wiring and end-to-end verification — ticket #164 (`Frontend/Issue-164/donor-dashboard-reports-link`) — depends on 5

- [ ] 6.1 Replace `DonorDashboard.tsx`'s disabled "View Reports" button with a `Link` to that budget's report list (`/budgets/:id` with the Reports section, or directly to `/budgets/:id/reports/:reportId` if the budget has exactly one report — implementation-time call per design.md's open question)
- [ ] 6.2 Update or add to `DonorDashboard.test.tsx` covering the now-enabled "View Reports" link
- [ ] 6.3 Manually exercise the full flow against the running dev stack: confirm a budget → create a report → add lines → upload an attachment → submit → review as funder (approve or reject) → if rejected, reopen and confirm edits are allowed again → view the same flow from the donor dashboard
- [ ] 6.4 Run the frontend test suite + `npm run lint` clean; PR merged

## 7. Currency ledger — funding receipts & conversions — ticket #165 (`Frontend/Issue-165/currency-ledger-ui`) — depends on 1 only; BLOCKED on backend ticket #148

- [ ] 7.1 Before starting: confirm `services/budget` has merged ticket #148 — `funding_receipt_routes.py`/`currency_conversion_routes.py` and `shared/schemas/currency_ledger_schema.py` must actually exist. Do not begin implementation against a nonexistent backend.
- [ ] 7.2 Add `location /api/v1/funding-receipts/` and `/api/v1/currency-conversions/` blocks to both `nginx/nginx-dev.conf` and `nginx/nginx.conf`, mirroring the pattern used for `/reports/` in ticket 1
- [ ] 7.3 Extend `frontend-typescript/src/pages/Budgets/types/budget.ts` with `FundingReceipt` and `CurrencyConversion` types matching `shared/schemas/currency_ledger_schema.py`
- [ ] 7.4 Create `frontend-typescript/src/api/currencyLedgerApi.ts`: `createFundingReceipt`, `listFundingReceiptsByBudget`, `createCurrencyConversion`, `listCurrencyConversionsByBudget`
- [ ] 7.5 Add `actual_currency` as an editable field to `SingleBudgetView.tsx`'s inline edit-mode metadata grid (alongside name/funder/duration), wired through the existing `editBudget` call
- [ ] 7.6 Add `frontend-typescript/src/pages/Budgets/components/CurrencyLedgerPanel.tsx`: shows a "set actual currency first" prompt (linking into edit mode) when `budget.actual_currency` is unset; otherwise shows funding-receipt and currency-conversion recording forms plus a chronological history list, each conversion row showing its implied rate (donor amount ÷ local amount) — no aggregate balance figure, per design.md's explicit non-goal
- [ ] 7.7 In the same panel, show a "received to date" figure: sum `listFundingReceiptsByBudget`'s amounts client-side and compare against `budget.total_amount` as a percentage/progress indicator when `budget.local_currency === budget.actual_currency`; otherwise show the two figures side by side with their own currency labels and no computed ratio, per design.md's currency-safe display decision
- [ ] 7.8 Mount `CurrencyLedgerPanel` inside `SingleBudgetView.tsx`'s non-edit-mode branch, visible only when `isBudgetOwner(budget, currentCustomerId)` is true
- [ ] 7.9 Add tests: prompt shown when `actual_currency` unset, forms shown once set, record-receipt/record-conversion happy paths, history list rendering with correct implied rate per row, received-to-date percentage shown only in the same-currency case (two-figure fallback otherwise), section hidden for non-owners
- [ ] 7.10 Run the frontend test suite + `npm run lint` clean; PR merged
