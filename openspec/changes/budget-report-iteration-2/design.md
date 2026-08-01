## Context

`Budget.total_amount` (`services/budget/app/models/budget.py:47`) is a derived field, kept in sync with the sum of `BudgetLine.amount` (spec'd in `donor-dashboard`'s "Budget total_amount stays in sync with its lines" requirement) — always in `local_currency`. `Budget.actual_currency` exists as a column but has no entry point anywhere in the frontend (noted as a gap in the prior `budget-report-frontend` change) and no numeric figure attached to it — it records *what currency the donor uses*, not *how much*. The currency-ledger feature (`budget-currency-ledger` spec, `CurrencyLedgerPanel.tsx`) records real bank events after the fact — `FundingReceipt` (money landed) and `CurrencyConversion` (donor amount ↔ local amount, rate derived from the two, never entered) — and is deliberately conservative about not inventing numbers: it only ever reflects transactions that actually happened.

This change adds a *planning-time* counterpart that the ledger intentionally doesn't cover: at budget-creation time, before any real money has moved, a grantee typically knows only "the donor is giving us €10,000" and needs a live local-currency guide to build against — not a figure computed only after the budget is already fully built (by which point it's too late to know, line by line, whether they're tracking under or over the donor's promise). There is currently no field to hold "€10,000" at all, nor any rate a grantee can pick and rely on while building.

There's also no record of *when* a budget's numbers were locked in. `Budget` has only `AuditMixin`'s generic `created_at`/`updated_at` — and a confirmed budget can later be reverted to `draft` and re-confirmed (`update_budget_service`'s `is_reverting` path, `services/budget/app/services/budget_services.py:170-182`), so `updated_at` doesn't reliably mean "when this was confirmed." A full transition-history table (every confirm/revert/reject event, who did it, when) is a real, separate need — already tracked as GitHub issue #138 — but is out of scope here: this is pre-launch, demo-stage work with no real user history at risk of being lost yet, so a single `confirmed_at` timestamp is enough for now.

**Reports directory.** `GET /reports/by-budget/{budget_id}` (`services/budget/app/api/report_routes.py`) is the only report-list route; the CRUD layer underneath (`report_crud.py`'s `list_reports`) already accepts `budget_id: UUID | None`, but `list_reports_service` always requires one and authorizes via `get_viewable_budget`, so nothing today lists across budgets. The frontend's `/reports` sidebar link (`DashboardLayout.tsx`) has no matching route in `App.tsx` and silently redirects to `/dashboard` via the catch-all route.

**Grantee dashboard.** `Dashboard.tsx` is fully hardcoded (mock `stats` array, static "Recent Activity") and fetches nothing. The only real aggregate endpoints today are donor-only (`/budgets/funded/summary`, `/budgets/funded/grantees`, `/budgets/funded/`, all gated by `require_donor`) — there's no owner/grantee equivalent, and no endpoint aggregates `FundingReceipt`/`CurrencyConversion` across more than one budget at a time (every ledger read, including `GET /currency-conversions/balance/{budget_id}`, is single-budget). The per-budget FIFO ledger logic (`get_ledger_balance_service`) already keeps each budget's converted/consumed/remaining local-currency figures separately tracked — this matters because in practice a grantee often runs multiple donor-funded budgets out of one pooled local-currency bank account (the alternative being a dedicated account per project purely for accounting separation); the ledger already earmarks each budget's slice internally, it's just never been surfaced in aggregate.

## Goals / Non-Goals

**Goals:**
- Let a budget owner record the donor's stated total commitment in `actual_currency` (`donor_total_amount`), separate from the local-currency `total_amount` that's derived from budget lines.
- Let the grantee enter their own estimated exchange rate up front — a live guide while building, not a figure only knowable after the budget is finished — and have it persist across sessions (draft, close, resume).
- Record when a budget was confirmed, as a lightweight anchor for "as of when was this estimate treated as final."
- Let anyone viewing a budget or its lines see figures in the donor's currency (as an estimate), not just local currency.
- Let a user see every report across every budget they have access to in one place, filterable by status/budget/donor, and fix the dead `/reports` nav link.
- Give a grantee a real, data-backed picture of their overall position: budgets by status, what's committed/received/converted per donor currency (never blended), and how a shared local-currency bank balance splits across their budgets.

**Non-Goals:**
- Do not build a full status-transition history table (#138) — backlogged; revisit once there's real production history worth protecting.
- Do not touch the real currency-ledger's rate logic (`CurrencyConversionModel`, FIFO allocation) — the estimated rate here is planning-only and never feeds into or reads from ledger allocation.
- Do not auto-generate or auto-scale budget lines from `donor_total_amount`/`estimated_exchange_rate` — the grantee still builds lines manually; this only records and displays the target.
- Do not extend `DonorDashboard`'s aggregate `total_allocated`/`total_allocated_by_currency` figures to show donor-currency equivalents — that's a follow-on to the existing mixed-currency-aggregation work, not bundled here.
- Do not build a per-line actual-FX trace for the `Used` column — the donor-currency figures in the lines table toggle are explicitly derived from the single estimated rate, not the ledger's real per-lot allocation (which stays out of scope, same as it was in `budget-report-frontend`).
- Do not add a "reconcile against a manually-entered real bank balance" feature to the dashboard — it surfaces and trusts what the ledger already tracks, it doesn't validate that against anything external.
- Do not extend the reports directory or dashboard to donor-role users beyond reusing the existing owner-vs-donor scoping pattern already established for `/budgets/` vs `/budgets/funded/` — no new permission model.

## Decisions

**1. The exchange rate is directly entered by the grantee, not derived.**
Reversed from an earlier version of this design, which derived a rate from `total_amount / donor_total_amount` after the fact. That doesn't work for the actual workflow: the grantee needs a rate to build *against*, before (or while) lines exist, so a derived rate — meaningless until the budget is finished — can't serve as a live guide. `estimated_exchange_rate` is therefore a real, directly-entered column (`actual_currency` → `local_currency`, e.g. `0.8`), persisted from the moment the grantee types it in so a saved-and-resumed draft doesn't lose it.
*Alternative considered*: derive the rate from `total_amount`/`donor_total_amount` (the original design). Rejected per the above — it inverts the actual order of the workflow.
*Alternative considered*: don't persist it at all, keep it as ephemeral client-side form state. Rejected — grantees work across multiple sessions; an unsaved rate would be lost on browser close, defeating the point of giving them a stable reference to build against.

**2. `donor_total_amount × estimated_exchange_rate` is a derived display figure ("estimated local cap"), not its own stored column.**
Both inputs are already stored directly; multiplying them at read time avoids a third figure that could drift out of sync if either input changes. Exposed as a computed field (e.g. `estimated_local_cap`) alongside the two inputs wherever a budget is returned. `null` when either input is unset or `donor_total_amount`/`estimated_exchange_rate` is 0.

**3. `donor_total_amount` and `estimated_exchange_rate` are metadata, locked the same way as other budget metadata.**
Both added to `_is_metadata_edit` (`services/budget/app/services/budget_services.py:82`) alongside `local_currency`/`actual_currency`, so they're editable pre-confirmation and frozen once `status == confirmed`, via the existing `is_budget_locked` check. No new locking mechanism.

**4. `confirmed_at` is a plain scalar timestamp, set on confirm and reset on re-confirm — not a history log.**
Set in `update_budget_service`'s confirm-transition branch (`services/budget/app/services/budget_services.py:196` onward) the moment `status` becomes `confirmed`; cleared (or left to be overwritten) if the budget is later reverted to `draft` and confirmed again, so it always reflects the *most recent* confirmation. This deliberately does not capture the full history of confirm/revert/reject cycles — that's issue #138's job, backlogged (see Non-Goals). `confirmed_at` answers "as of when was the current `estimated_exchange_rate` treated as final," not "show me every status change this budget ever went through."

**5. Donor-currency line figures are a display-layer conversion, not a stored per-line amount.**
`BudgetLine` gets no new column. The lines-table toggle multiplies each line's local `amount` (and each line's `spendByLineId` "used" figure) by `estimated_exchange_rate` at render time. This keeps the estimate honestly approximate and uniform across all lines — matching how the ledger already refuses to fabricate a per-line real-FX trace — rather than implying a precision the data doesn't support.
*Alternative considered*: let each budget line carry its own donor-currency amount, entered independently. Rejected — it would let a line's local and donor figures diverge from the budget-level rate with no reconciliation rule, defeating the "estimate" framing and reopening exactly the kind of duplicated-aggregation risk already hit once (mixed-currency donor-dashboard bug).

**6. Toggle state is local UI state, not persisted.**
"Local / Donor (estimated) / Both" is a `useState` in `BudgetViewLinesTable.tsx`, not a user preference stored anywhere — same footprint as any other client-side view toggle already in this codebase, no new API surface.

**7. Reports directory loosens an existing constraint rather than introducing a new pattern.**
`list_reports_service` already sits on top of a CRUD function that accepts `budget_id: UUID | None`; the new `GET /reports/` route relaxes the service layer to allow an unset `budget_id`, scoping instead to "every budget visible to this user" — the exact same owner-vs-donor split already implemented for `/budgets/` vs `/budgets/funded/`. No new authorization model, just applying the existing one to a second resource.
*Alternative considered*: a denormalized read-model/materialized view joining Report+Budget for faster cross-budget queries. Rejected as premature — data volumes here are small (nonprofit-scale, not high-throughput), a `joinedload` is more than adequate, and a read-model adds sync complexity with no current justification.

**8. The dashboard's "committed" figure is computed from `total_amount`, not `donor_total_amount`.**
Per the correction during scoping: `donor_total_amount` is the donor's promise, but what actually got built into budget lines (`total_amount`, real and derived) can undershoot that promise. Showing the promise as "committed" would overstate what's actually allocated. So the dashboard computes, per confirmed budget, `total_amount ÷ estimated_exchange_rate` (converting the real local total back into the donor's currency) and sums that across budgets, grouped by `actual_currency`. Budgets with no `actual_currency`/`estimated_exchange_rate` set are excluded from this currency-grouped figure entirely (nothing to convert, consistent with the "never blend" rule) — not folded into any other currency's total.

**9. The per-budget breakdown table reuses `get_ledger_balance_service` as-is; the three currency-grouped totals are new grouped-sum queries.**
The hard part here — FIFO-consuming report-line expenses against currency-conversion lots, per budget — already exists and is correct; the dashboard doesn't reimplement it, it calls the existing per-budget balance function once per confirmed budget and lists the results as rows (`Budget | Donor | Local converted | Local spent | Local remaining`). Summing the "remaining" column across all confirmed budgets is a natural cross-check that the ledger's per-budget earmarking of a single pooled bank account adds up to something coherent, and is worth surfacing as its own total. The three currency-grouped cards (committed, received, converted-with-%) are genuinely new: straightforward `GROUP BY currency` aggregate queries over `Budget`/`FundingReceipt`/`CurrencyConversion`, scoped to `status = confirmed`, with no FIFO logic involved.

**10. Both new endpoints are read-only aggregations — no new tables, no new domain concepts.**
The reports directory needs an eager-load and a wider filter; the dashboard needs grouped sums plus a loop over an existing per-budget function. Neither introduces new persisted state, keeping both additions comparatively low-risk relative to the schema changes in Decisions 1-4.

## Risks / Trade-offs

- [A grantee-entered rate can be stale by the time the budget is confirmed, especially if they set it early and confirm weeks later] → Accepted: it's editable at any point pre-confirmation, so the grantee can refresh it right before confirming; `confirmed_at` documents when it was locked in, so later readers know how fresh (or not) it was, without the system pretending precision it doesn't have.
- [Estimated figures can look authoritative even though they're planning guesses] → Every donor-currency figure derived from them (budget total equivalent, line-table toggle) is labeled "estimated" in the UI, and the real currency-ledger panel remains the source of truth for what actually happened financially.
- [Two "rate" concepts in the same product — estimated (this change, grantee-entered) vs. real/derived (currency-ledger, bank-derived) — could confuse users if not visually distinguished] → Keep the two UI surfaces separate (budget header/lines-table vs. `CurrencyLedgerPanel`) and always pair the estimated figure with the word "estimated"; don't merge them into one combined rate display.
- [`confirmed_at` alone loses the story of a budget confirmed/reverted/reconfirmed multiple times] → Accepted for now per the Non-Goals; issue #138 is the place to revisit this once it matters (real users, real history worth protecting).
- [The "committed" figure depends on `estimated_exchange_rate` being set and reasonably fresh — a confirmed budget with a stale or missing rate silently drops out of that currency's total] → Acceptable given Decision 8's "exclude rather than misrepresent" rule; the per-budget breakdown table still shows that budget's real local-currency figures regardless, so nothing is hidden, just not folded into the donor-currency-grouped card.
- [Cross-budget dashboard queries (grouped sums + a per-budget loop) could get slow as the number of budgets grows] → Not a concern at current/expected scale (nonprofit-scale data volumes, small number of budgets per grantee); revisit only if it becomes real.

## Migration Plan

- Additive-only: one migration adding `budgets.donor_total_amount` (nullable float), `budgets.estimated_exchange_rate` (nullable float), and `budgets.confirmed_at` (nullable timestamp). No backfill needed — existing budgets simply have none of these set, identical to their current state; `confirmed_at` stays `null` for already-confirmed budgets rather than being backfilled from `updated_at` (which, per Context, isn't a reliable proxy).
- No rollback complexity: dropping the columns (if ever reverted) loses no derived data, since `estimated_local_cap` is never persisted.
- Reports directory and dashboard endpoints are pure additions (no schema changes) — no migration involved, only new routes/services/schemas.
