Workflow rule: **one group = one GitHub ticket = one PR, merged before the next group starts.** Tickets are already created (see each group's heading); branch per ticket as shown. Do not start a group until the previous one's PR is merged. Every PR: backend `flake8 --max-line-length=100` / frontend `npm run lint` clean; commits/pushes only with explicit user approval.

## 1. Backend: donor commitment, estimated rate, confirmed_at — ticket #179 (`Budget/Issue-179/donor-commitment-fields`)

- [x] 1.1 Add a migration for `budgets.donor_total_amount` (nullable float), `budgets.estimated_exchange_rate` (nullable float), and `budgets.confirmed_at` (nullable timestamp). No backfill. — `000009_add_budget_donor_commitment_fields.py` (down_revision `000008`), verified `alembic upgrade head`/`downgrade -1`/`upgrade head` against real local Postgres.
- [x] 1.2 Add the three fields to `BudgetModel` (`services/budget/app/models/budget.py`).
- [x] 1.3 Add `donor_total_amount`/`estimated_exchange_rate` to `BudgetCreate`/`BudgetUpdate`/`BudgetPatched` and the budget response schema; add read-only `confirmed_at` and computed `estimated_local_cap` to the response schema (`services/budget/app/schemas/budget_schema.py`). — `BudgetPatched` doesn't exist on the backend (frontend-only type, correctly handled in ticket #180/group 2's 2.1); backend fields added to `BudgetBase` (covers `BudgetCreate`/`BudgetUpdate`) plus `confirmed_at`/`estimated_local_cap` added to `Budget` and `BudgetWithLines` (the latter is the actual `GET /budgets/{id}` response model).
- [x] 1.4 Add `donor_total_amount`/`estimated_exchange_rate` to `_is_metadata_edit` (`services/budget/app/services/budget_services.py:82-97`) so both are locked by the existing `is_budget_locked` / confirmed-budget check, same as `local_currency`/`actual_currency`.
- [x] 1.5 In `update_budget_service`'s confirm-transition branch (`services/budget/app/services/budget_services.py:196` onward), set `confirmed_at` to the current time on confirm; ensure it's set again (not left stale) if a budget is reverted to `draft` and confirmed a second time.
- [x] 1.6 Add `estimated_local_cap` as a computed field (`donor_total_amount × estimated_exchange_rate`; `null` when either input is unset or zero) assembled at read time, not persisted. — `_compute_estimated_local_cap` in `budget_services.py`, wired into `populate_budget_with_user_details`.
- [x] 1.7 Add/extend backend tests: set `donor_total_amount`/`estimated_exchange_rate` on an unconfirmed budget; reject the same updates on a confirmed budget; `confirmed_at` set on first confirm and updated on re-confirm after a revert; `estimated_local_cap` correct when both inputs are set, `null` when either is missing. — `tests/test_budget_donor_commitment.py` (12 new tests); also updated `test_budget_currency_fields.py`'s exact-kwargs assertion to account for the new `update_budget` call args.
- [ ] 1.8 Run `services/budget`'s tests and lint clean; PR merged. — tests/lint/mypy clean (207/207 passing, flake8 `--max-line-length=100` clean, black clean, mypy has only a pre-existing unrelated error); PR not yet opened/merged.

## 2. Frontend: donor commitment display — ticket #180 (`Frontend/Issue-180/donor-commitment-display`) — depends on 1

- [ ] 2.1 Add `donor_total_amount`, `estimated_exchange_rate`, `confirmed_at`, `estimated_local_cap` to `Budget`, and the first two to `BudgetUpdate`/`BudgetPatched` (`frontend-typescript/src/pages/Budgets/types/budget.ts`).
- [ ] 2.2 Add editable `donor_total_amount` and `estimated_exchange_rate` fields to the budget edit form, disabled under the same condition the form already disables `actual_currency` (confirmed budget).
- [ ] 2.3 Show the donor commitment, the estimated rate, and the estimated local cap alongside the real `total_amount` (labeled "estimated" where derived) wherever the single-budget view currently shows the total (`BudgetViewHeader.tsx` / `SingleBudgetView.tsx`), falling back to today's local-only display when `estimated_local_cap` is `null`.
- [ ] 2.4 Apply the same donor/local pairing to each budget's total in `DonorDashboard.tsx` wherever a per-budget `total_amount` is listed (not the aggregate `total_allocated` figure — that stays out of scope per design.md).
- [ ] 2.5 Add/extend tests for the edit form and both display sites covering: estimate shown when `estimated_local_cap` is set, local-only fallback when it's `null`.
- [ ] 2.6 Run the frontend test suite and lint clean; PR merged.

## 3. Frontend: budget-lines table currency toggle — ticket #181 (`Frontend/Issue-181/lines-currency-toggle`) — depends on 1

- [ ] 3.1 Add a Local / Donor (estimated) / Both toggle to `BudgetViewLinesTable.tsx`, rendered only when `budget.estimated_exchange_rate` is non-null; hidden otherwise (identical to current behavior).
- [ ] 3.2 Convert the `Amount` column per the selected toggle state using `estimated_exchange_rate`, labeling donor/both figures as estimated.
- [ ] 3.3 Convert the `Used` column (`UsedPill`, both the desktop table and the mobile card layout) the same way, including its category-subtotal rendering.
- [ ] 3.4 Add/extend `BudgetViewLinesTable.test.tsx` covering: toggle hidden when `estimated_exchange_rate` is `null`, and correct Local/Donor/Both rendering for `Amount` and `Used` when it's set.
- [ ] 3.5 Run the frontend test suite and lint clean; PR merged.

## 4. Backend: cross-budget reports directory — ticket #182 (`Budget/Issue-182/reports-directory-api`)

- [ ] 4.1 Add `GET /reports/` to `report_routes.py`, accepting optional `status`, `budget_id`, `funding_customer_id` query params, scoped by role the same way `/budgets/` (owner) vs `/budgets/funded/` (donor) already split.
- [ ] 4.2 Relax `list_reports_service`/add a new service function that accepts an optional `budget_id` (reusing `report_crud.list_reports`'s existing `budget_id: UUID | None` support) and authorizes against "all budgets visible to this user" instead of a single budget.
- [ ] 4.3 Extend the report response schema with the parent budget's `name`, `status`, and funder (`funding_customer_id`/`external_funder_name`), populated via eager-load (`joinedload` on `Report.budget`) rather than a per-row lookup.
- [ ] 4.4 Add/extend backend tests: owner sees reports across all their budgets; donor sees reports across all budgets they fund; `status`/`budget_id`/`funding_customer_id` filters individually and combined; budget/funder fields present on each returned report.
- [ ] 4.5 Run `services/budget`'s tests and lint clean; PR merged.

## 5. Frontend: reports directory page — ticket #183 (`Frontend/Issue-183/reports-directory-ui`) — depends on 4

- [ ] 5.1 Add the new reports-directory page and its `/reports` route in `App.tsx`, fixing the dead nav link in `DashboardLayout.tsx`.
- [ ] 5.2 Build the table with columns Report / Budget / Donor / Period / Status / Actions (View Report, View Budget), reusing the existing status-badge styling and mobile-card fallback pattern from `BudgetReportsPage.tsx`.
- [ ] 5.3 Add filter controls for status, budget, and donor, wired to the new `GET /reports/` endpoint's query params.
- [ ] 5.4 Add the empty-state treatment consistent with existing empty states elsewhere in the app.
- [ ] 5.5 Add/extend frontend tests covering: columns render correctly, each filter narrows results, View Budget navigates to the right budget, mobile card fallback, empty state.
- [ ] 5.6 Run the frontend test suite and lint clean; PR merged.

## 6. Backend: grantee dashboard aggregation — ticket #184 (`Budget/Issue-184/grantee-dashboard-api`) — depends on 1

- [ ] 6.1 Add a new grantee-dashboard summary endpoint (e.g. `GET /budgets/dashboard/summary`) returning: budget counts by status; committed/received/conversion-progress figures grouped by `actual_currency` (confirmed budgets only); a per-budget breakdown array.
- [ ] 6.2 Implement the committed-by-currency aggregation as `total_amount ÷ estimated_exchange_rate` per confirmed budget, summed per `actual_currency`, excluding budgets missing `actual_currency`/`estimated_exchange_rate`.
- [ ] 6.3 Implement the received-by-currency and conversion-progress-by-currency aggregations from `FundingReceipt`/`CurrencyConversion`, scoped to confirmed budgets, grouped by currency.
- [ ] 6.4 Implement the per-budget breakdown by calling the existing `get_ledger_balance_service` once per confirmed budget (no new FIFO/allocation logic) and assembling the results with budget name/funder.
- [ ] 6.5 Add/extend backend tests: status counts correct; committed total uses `total_amount`/`estimated_exchange_rate` not `donor_total_amount`; budgets missing a usable rate are excluded from (not folded into) currency totals; conversion percentage computed correctly per currency; breakdown includes one row per confirmed budget with correct converted/spent/remaining figures.
- [ ] 6.6 Run `services/budget`'s tests and lint clean; PR merged.

## 7. Frontend: grantee dashboard — ticket #185 (`Frontend/Issue-185/grantee-dashboard-ui`) — depends on 6

- [ ] 7.1 Replace `Dashboard.tsx`'s hardcoded `stats` array and static "Recent Activity" with data fetched from the new summary endpoint.
- [ ] 7.2 Render budget-status counts, and the committed/received/conversion-progress figures as separate per-currency stat cards (never blended across currencies).
- [ ] 7.3 Render the per-budget breakdown table (Budget / Donor / Converted / Spent / Remaining, in local currency).
- [ ] 7.4 Add/extend frontend tests covering: multiple currencies render as separate figures, conversion percentage displayed correctly, breakdown table renders one row per confirmed budget.
- [ ] 7.5 Run the frontend test suite and lint clean; PR merged.
