## Context

`frontend-typescript/src/pages/Budgets/` follows an established pattern: a page-level `SingleBudgetViewContext` (React Query-backed) feeds a `SingleBudgetView` composed of small presentational components (`BudgetViewHeader`, `BudgetViewLinesTable`, `BudgetViewSummary`, `BudgetViewTraces`), with `AddBudgetLine`/`EditBudget` as modals. API calls live in thin functions in `src/api/budgetApi.ts` / `src/api/gatewayApi.ts` (axios instance pointed at `VITE_API_GATEWAY`, default `http://localhost:8082/api/v1`). This change adds a parallel `Report`/`ReportLine`/`Attachment` slice following the same shape, plus a small confirmation action on the existing budget view.

The backend (tickets #144–#147, implemented in a separate concurrent session) exposes:
- `POST/GET/PATCH/DELETE /api/v1/reports/`, `GET /reports/by-budget/{budget_id}`, `POST /reports/{id}/submit`, `POST /reports/{id}/review`, `POST /reports/{id}/reopen`
- `POST/GET/PATCH/DELETE /api/v1/report-lines/`, `GET /report-lines/by-report/{report_id}`
- `POST /api/v1/attachments/` (multipart), `GET /attachments/by-report-line/{report_line_id}`, `GET /attachments/{id}/content` (streaming download), `DELETE /attachments/{id}/`

**Forward-compat note (2026-07-26):** a new ticket (#157, in `budget-reports`) is adding `GET /attachments/{id}/download-url`, which 307-redirects to a short-lived presigned URL instead of streaming bytes through the app. `downloadAttachment` in `reportApi.ts` (task 1.7) can point at that route instead of `/content` once #157 merges and bucket CORS is configured — no change to the `<a>`/blob-trigger UX either way, since a redirect target still carries `Content-Disposition`. Not required for this change to ship; noted so whoever implements task 5.2 doesn't have to rediscover this.

None of these routes are yet proxied by the gateway nginx configs (`nginx/nginx.conf`, `nginx/nginx-dev.conf` only proxy `/budgets/` and `/budget-lines/` to the budget upstream today) — that gap is closed as part of this change since without it the frontend has nothing to call.

Budget confirmation itself needs no new backend endpoint: `PATCH /budgets/{id}` already accepts `status`/`start_date` via `BudgetUpdate`, and `update_budget_service` (ticket #144) already rejects a `confirmed` transition when `start_date` is unset — the frontend only needs to collect `start_date` and send the existing PATCH.

## Goals / Non-Goals

**Goals:**
- Let a grantee confirm a budget (set `start_date`, transition to `confirmed`) directly from the single-budget view.
- Let a grantee draft, edit, and submit a report with report lines against a confirmed budget.
- Let a funder (or, when no in-system funder exists, the budget owner) review a submitted report and approve/reject it, and let a grantee reopen a rejected report.
- Let either party upload, view, download, and delete attachments on report lines while the parent report is a draft.
- Surface all of this identically from both the grantee's `SingleBudgetView` and the funder's `DonorDashboard` "View Reports" entry point.

**Non-Goals:**
- Currency ledger UI (`FundingReceipt`/`CurrencyConversion`/FIFO balances, ticket #148) — not started on the backend yet.
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

**Nginx changes mirror the existing `/budgets/`/`/budget-lines/` blocks exactly**, including the dev config's simpler `proxy_pass` (upstream already includes path) vs. the prod config's `rewrite ... break` + variable-`proxy_pass` pattern (needed there because Docker's embedded DNS resolver requires a variable, and variable-based `proxy_pass` doesn't do prefix rewriting automatically) — no new pattern introduced, just three more resource prefixes added to both files.

## Risks / Trade-offs

- **[Risk]** Client-side upload-limit duplication (15MB, PDF/JPEG/PNG/HEIC) can drift from the backend's actual `ALLOWED_CONTENT_TYPES`/size constant if either changes later without updating the other. → **Mitigation**: acceptable for v1 (backend remains authoritative, so drift only means a slightly wrong client-side error message, never a security gap); revisit exposing the limits via an endpoint or shared constant if this proves to bite in practice.
- **[Risk]** Role-gating via JWT `customer_id` comparison duplicates authorization logic that already lives on the backend (`_can_review`, owner-only checks) in a second place. → **Mitigation**: explicitly documented above as UI-only convenience; every gated action still round-trips through the real backend check, so a bug here can only hide a legitimate action, not expose an illegitimate one.
- **[Trade-off]** Report detail as its own route (vs. inline expansion) adds one more page to navigate for the common single-report-per-budget case. Accepted for consistency with the existing routing pattern and to support funder deep-linking from `DonorDashboard`.

## Migration Plan

No data migration — purely additive frontend code plus two nginx config edits (dev and prod). Nginx changes are a straight addition of new `location` blocks; rollback is reverting those two files. No feature flag: the confirmation action and Reports section only render once a budget reaches the relevant state (`draft`/`confirmed`), so existing budgets are unaffected until a user interacts with the new UI.

## Open Questions

- Whether `DonorDashboard`'s "View Reports" button should deep-link straight to a report list (current plan) or, when a budget has exactly one report, straight to that report's detail view — left as an implementation-time UX call, not blocking.
