## Context

`frontend-typescript/src/pages/Budgets/` follows an established pattern: a page-level `SingleBudgetViewContext` (React Query-backed) feeds a `SingleBudgetView` composed of small presentational components (`BudgetViewHeader`, `BudgetViewLinesTable`, `BudgetViewSummary`, `BudgetViewTraces`), with `AddBudgetLine`/`EditBudget` as modals. API calls live in thin functions in `src/api/budgetApi.ts` / `src/api/gatewayApi.ts` (axios instance pointed at `VITE_API_GATEWAY`, default `http://localhost:8082/api/v1`). This change adds a parallel `Report`/`ReportLine`/`Attachment` slice following the same shape, plus a small confirmation action on the existing budget view.

The backend (tickets #144–#147, implemented in a separate concurrent session) exposes:
- `POST/GET/PATCH/DELETE /api/v1/reports/`, `GET /reports/by-budget/{budget_id}`, `POST /reports/{id}/submit`, `POST /reports/{id}/review`, `POST /reports/{id}/reopen`
- `POST/GET/PATCH/DELETE /api/v1/report-lines/`, `GET /report-lines/by-report/{report_id}`
- `POST /api/v1/attachments/` (multipart), `GET /attachments/by-report-line/{report_line_id}`, `GET /attachments/{id}/content` (streaming download), `DELETE /attachments/{id}/`

**Presigned downloads (updated 2026-07-27):** `#157` (in `budget-reports`) merged `GET /attachments/{id}/download-url`, which 307-redirects to a short-lived presigned URL instead of streaming bytes through the app. `downloadAttachment` in `reportApi.ts` (task 1.7) now points at that route instead of `/content` — same `<a>`/blob-trigger UX, since the redirect target still carries `Content-Disposition`. Verified end-to-end against the dev stack (register → onboard → create/confirm budget → create report/report-line → upload attachment → `GET .../download-url`): the gateway 307s to a `localhost:9000` MinIO presigned URL, and MinIO already answers both the CORS preflight and the actual GET with `Access-Control-Allow-Origin: http://localhost:5173` and exposes `Content-Disposition` — the bucket's CORS policy is already configured for the frontend dev origin, so this works without further infra changes.

None of these routes are yet proxied by the gateway nginx configs (`nginx/nginx.conf`, `nginx/nginx-dev.conf` only proxy `/budgets/` and `/budget-lines/` to the budget upstream today) — that gap is closed as part of this change since without it the frontend has nothing to call.

Budget confirmation itself needs no new backend endpoint: `PATCH /budgets/{id}` already accepts `status`/`start_date` via `BudgetUpdate`, and `update_budget_service` (ticket #144) already rejects a `confirmed` transition when `start_date` is unset — the frontend only needs to collect `start_date` and send the existing PATCH.

**Currency ledger status (2026-07-26):** `budget-reports`'s ticket #148 (`FundingReceipt`/`CurrencyConversion`/FIFO allocation, plus a 2026-07-26 amendment requiring retroactive backfill of allocation rows against outstanding unsatisfied expenses when a new conversion lands — see that change's `design.md` and `specs/budget-currency-ledger/spec.md`) is fully specced but **not implemented**: `tasks.md` group 5 is entirely unchecked, and no `currency_ledger.py` model/`funding_receipt_routes.py`/`currency_conversion_routes.py` exist in `services/budget` yet. The planned routes are CRUD-only (`POST/GET /funding-receipts/`, `POST/GET /currency-conversions/`, both scoped to the budget owner) — there is no planned endpoint returning an aggregate per-currency unconsumed balance or a report-line's allocation trail. This frontend capability is designed now so it's ready to build the moment #148 merges, but ticket 3 (see tasks.md) cannot start implementation until then.

## Goals / Non-Goals

**Goals:**
- Let a grantee confirm a budget (set `start_date`, transition to `confirmed`) directly from the single-budget view.
- Let a grantee draft, edit, and submit a report with report lines against a confirmed budget.
- Let a funder (or, when no in-system funder exists, the budget owner) review a submitted report and approve/reject it, and let a grantee reopen a rejected report.
- Let either party upload, view, download, and delete attachments on report lines while the parent report is a draft.
- Let a budget owner record a funding receipt and a currency conversion against a budget, and see both as a chronological history, once the backing endpoints exist.
- Let a budget owner see how much has been received so far toward the budget's total (e.g. two £20,000 receipts against a £100,000 budget), without inventing a second "commitment amount" field.
- Surface all of this identically from both the grantee's `SingleBudgetView` and the funder's `DonorDashboard` "View Reports" entry point.

**Non-Goals:**
- Aggregate per-currency unconsumed-balance display, and any UI showing which conversion(s) fund a given report-line expense (the FIFO allocation trail) — no backend summary endpoint exists for either; computing them client-side would mean re-implementing FIFO-with-retroactive-backfill logic in two places, which is a correctness liability, not a convenience. Revisit once the backend exposes a summary.
- Cross-hop rollup UI (`ReportLine.source_report_id`) — unscoped on the backend too.
- A general role/permission system — reuses the same owner/funder distinction already encoded in `Budget.owner`/`Budget.funding_customer_id`.
- Presigned/direct-to-storage upload — uploads proxy through the browser → gateway → budget app, matching the backend's v1 design.

## Decisions

**New `src/api/reportApi.ts` module, not folding onto `budgetApi.ts`.**
Reports/report-lines/attachments are a distinct resource family with their own base paths (`/reports`, `/report-lines`, `/attachments`) and, for attachments, a different content type (`multipart/form-data` for upload, blob response for download). Keeping them in one file mirrors how `donorDashboardApi.ts` is already split out from `budgetApi.ts` by resource family, and keeps `budgetApi.ts` focused on budget/budget-line CRUD.

**Role/permission gating is UI-only convenience, never the source of truth.**
The frontend decodes `customer_id` out of the existing JWT (`safeDecodeToken`, already used by `AuthContext` for `is_ngo`/`is_donor`) and compares it to `budget.funding_customer_id` (funder) or `budget.owner?.id` (owner) to decide which buttons to show (Submit/Review/Reopen, upload/delete). The backend re-checks all of this independently on every call (`_can_review`, owner-only locks, etc.) — the frontend check exists purely to avoid showing an action a request would 403 on, not to enforce anything. A stray or stale JWT claim degrades to hiding a button, never to exposing one the backend would reject.

**Report detail is a new route (`/budgets/:id/reports/:reportId`), not a modal.**
A report can contain many lines each with multiple attachments — modal-in-modal (report line edit, then attachment upload) would nest three levels deep. A dedicated route matches the existing `/budgets/:id` pattern and lets a funder deep-link to a specific report from the `DonorDashboard`.

**Reports list lives inline in `SingleBudgetView`, not a separate route.**
Unlike report detail, the list itself is small (most budgets have one or a handful of reports) and belongs next to the budget it reports against, the same way `BudgetViewLinesTable` sits inline today. Gated to render only when `budget.status === "confirmed"` or the budget already has reports (a `confirmed` budget that was later `archived` should still show its historical reports).

**Budget confirmation is a small inline action on `BudgetViewHeader`/`SingleBudgetView`, not a separate modal-heavy flow.**
Only one new field (`start_date`) is required beyond the existing status transition, so a lightweight inline date input + "Confirm Budget" button (visible only when `budget.status` is `draft` and `budget.start_date` is unset, disabled until a date is picked) is proportionate — consistent with how `SingleBudgetView` already handles inline edit mode rather than a modal for budget metadata edits.

**Client-side upload validation (size ≤ 15MB, content-type allowlist) duplicates the backend's constraints.**
Rejecting an oversized/unsupported file before the network round-trip is a UX nicety (immediate feedback vs. waiting for a 4xx), not a security boundary — the backend's own validation (`upload_attachment_service`) remains authoritative and is not weakened by this. The two lists must be kept in sync by hand since there's no shared schema constant exposed to the frontend today; noted as a minor duplication risk below.

**Currency ledger UI ships as "record + raw chronological list" only, with no computed balance figure.**
A funding receipt or conversion's own fields (donor amount, local amount, dates) are safe to display as-is, and a per-row implied rate (`donor_amount / local_amount`) is safe to compute client-side — it's arithmetic on two numbers the backend already returned for that one row, not a cross-row aggregation. An unconsumed *balance*, by contrast, depends on every report-line expense's FIFO allocation against these lots, including the retroactive-backfill rule (a later conversion can reach back and satisfy an earlier overspend) — replicating that in the frontend would be a second, independently-maintained implementation of the exact allocation algorithm the backend owns. This codebase already hit this failure mode once (the pre-fix donor-dashboard blended totals across currencies instead of trusting a backend-grouped figure — see the `Mixed Currency Aggregation Fix`); the lesson here is the same shape of bug, one level deeper (temporal allocation order, not just currency grouping). Balance display is deferred until the backend exposes it as a computed field/endpoint, not approximated now.

**New `src/api/currencyLedgerApi.ts` module, mirroring the `reportApi.ts` split.**
`/funding-receipts` and `/currency-conversions` are their own resource family with their own base paths, separate from reports/attachments — same reasoning as the `reportApi.ts` vs. `budgetApi.ts` split above.

**Currency ledger section requires `Budget.actual_currency` to be set; `actual_currency` becomes editable via the existing inline budget-edit form.**
The backend's `FundingReceipt` is denominated in `budget.actual_currency` (the contract's wire-transfer currency), but that field currently has zero frontend UI — it's declared on the backend model (ticket #144) and was only ever added to the frontend's `Budget` type as a display-only field by this same change's task 1.4. Rather than invent a separate one-off input just for the ledger flow, it's added as a fourth field on `SingleBudgetView.tsx`'s existing inline edit-mode grid (name/funder/duration today), consistent with how that same form already handles budget metadata. The ledger section itself shows a "set your actual currency first" prompt (linking into edit mode) instead of the record forms when `actual_currency` is unset.

**"Received to date" reuses the existing `Budget.total_amount` as the comparison target — no new backend field.**
The multi-tranche part of "donor confirms £100,000, transfers £20,000, then another £20,000 later" is already fully covered by `FundingReceipt` (#148) — each transfer is just another receipt row, and summing `FundingReceipt.amount` across all of a budget's receipts is a plain sum over already-fetched rows (no FIFO/allocation knowledge needed, unlike the unconsumed-balance figure deferred above), so it's safe to compute client-side. What was missing was a *target* to compare that sum against. An earlier version of this decision proposed a new `Budget.committed_amount` field for that target — rejected: `Budget.total_amount` already exists (sum of budget-line amounts, ticket #133) and is exactly "the budget's total" in the everyday case; adding a second, near-duplicate total field was solving a problem that doesn't need solving. The one real subtlety: `total_amount` is denominated in `local_currency` (it's a sum of budget-line amounts, and lines are entered in local currency), while `FundingReceipt.amount` is denominated in `actual_currency` — the same currency-plurality this whole design has been careful about elsewhere. So the frontend shows a received/total percentage or progress bar **only when `budget.local_currency === budget.actual_currency`** (the common case, where the two figures are directly comparable); when they differ, it shows "Received to date: X `actual_currency`" and "Budget total: Y `local_currency`" as two separate figures with no computed ratio between them — the same "group by currency, never blend" rule as `total_allocated_by_currency` on the donor dashboard, applied to a currency-*mismatch* case rather than a currency-*mixing* one.

**Currency ledger section is owner-only, matching the backend's route scoping.**
`funding_receipt_routes.py`/`currency_conversion_routes.py` are planned as owner-scoped (per `budget-reports`' tasks.md 5.13/5.14) — no funder-review concept applies here, unlike reports. The frontend hides the whole section from anyone who isn't `isBudgetOwner(budget, currentCustomerId)` (task 1.8's helper), for the same UI-only-convenience reason documented above for report review gating.

**Nginx changes mirror the existing `/budgets/`/`/budget-lines/` blocks exactly**, including the dev config's simpler `proxy_pass` (upstream already includes path) vs. the prod config's `rewrite ... break` + variable-`proxy_pass` pattern (needed there because Docker's embedded DNS resolver requires a variable, and variable-based `proxy_pass` doesn't do prefix rewriting automatically) — no new pattern introduced, just three more resource prefixes added to both files.

## Risks / Trade-offs

- **[Risk]** Client-side upload-limit duplication (15MB, PDF/JPEG/PNG/HEIC) can drift from the backend's actual `ALLOWED_CONTENT_TYPES`/size constant if either changes later without updating the other. → **Mitigation**: acceptable for v1 (backend remains authoritative, so drift only means a slightly wrong client-side error message, never a security gap); revisit exposing the limits via an endpoint or shared constant if this proves to bite in practice.
- **[Risk]** Role-gating via JWT `customer_id` comparison duplicates authorization logic that already lives on the backend (`_can_review`, owner-only checks) in a second place. → **Mitigation**: explicitly documented above as UI-only convenience; every gated action still round-trips through the real backend check, so a bug here can only hide a legitimate action, not expose an illegitimate one.
- **[Trade-off]** Report detail as its own route (vs. inline expansion) adds one more page to navigate for the common single-report-per-budget case. Accepted for consistency with the existing routing pattern and to support funder deep-linking from `DonorDashboard`.
- **[Risk]** Shipping the currency ledger UI as "record + list" without any balance figure may read as incomplete to a user expecting to see "how much of my £10,000 is still unconverted" right away. → **Mitigation**: explicitly scoped as a Non-Goal above rather than faked with a client-side approximation that could disagree with the backend once it does compute one; flagged to the user as a real product gap, not silently worked around. Fast-follow once the backend adds a summary endpoint.
- **[Risk]** This whole capability (tasks.md ticket 3) is blocked on a concurrent session's backend work (ticket #148) that hadn't started implementation as of 2026-07-26. → **Mitigation**: speced now so no time is lost once it lands; tasks.md explicitly calls out the blocker rather than letting someone start it against nonexistent endpoints.

## Migration Plan

No data migration — purely additive frontend code plus two nginx config edits (dev and prod). Nginx changes are a straight addition of new `location` blocks; rollback is reverting those two files. No feature flag: the confirmation action, Reports section, and currency-ledger section only render once a budget reaches the relevant state (`draft`/`confirmed`/`actual_currency` set), so existing budgets are unaffected until a user interacts with the new UI. The currency-ledger section additionally can't go live at all until backend ticket #148 ships its endpoints — deploying this frontend code early just means that section stays invisible (no `actual_currency` ever gets set, or its record calls 404) until then, not broken.

## Open Questions

- Whether `DonorDashboard`'s "View Reports" button should deep-link straight to a report list (current plan) or, when a budget has exactly one report, straight to that report's detail view — left as an implementation-time UX call, not blocking.
- Whether the backend should add a per-currency balance summary endpoint (and/or a per-report-line allocation-trail endpoint) as part of ticket #148 itself or as its own fast-follow ticket — this is a real, user-visible gap this design surfaced, not resolved here since it's the other session's backend scope to decide.
