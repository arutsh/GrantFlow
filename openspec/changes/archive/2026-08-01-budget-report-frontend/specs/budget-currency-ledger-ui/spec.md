## ADDED Requirements

### Requirement: Actual currency required before ledger use
The frontend SHALL require `Budget.actual_currency` to be set before showing the funding-receipt/currency-conversion recording forms, since a receipt is denominated in that currency, and SHALL let the budget owner set it via the existing budget-edit form.

#### Scenario: Ledger prompts for actual currency when unset
- **WHEN** the budget owner opens the currency ledger section on a budget with no `actual_currency` set
- **THEN** the frontend shows a prompt to set the actual currency (linking into the budget-edit form) instead of the recording forms

#### Scenario: Ledger forms available once actual currency is set
- **WHEN** `budget.actual_currency` is set
- **THEN** the currency ledger section shows the funding-receipt and currency-conversion recording forms

### Requirement: Currency ledger visible to owner or funder; recording stays owner-only

> **Amended 2026-08-01**: broadened from owner-only after a backend code review pass made the read endpoints (`list_funding_receipts_service`/`list_currency_conversions_service`/`get_ledger_balance_service`) viewable by the funder too (`get_viewable_budget`, not `_get_owned_budget`), matching how report visibility already works between grantee and funder.

The frontend SHALL show the currency ledger section (balance figures and history) to the budget owner or the matching funder, and SHALL show the "Record Payment Received"/"Record Conversion" actions and the "set actual currency" action only to the owner.

#### Scenario: Unrelated viewer does not see the ledger section
- **WHEN** the current user is neither the budget's owner nor its matching funder
- **THEN** the single-budget view does not show the currency ledger section

#### Scenario: Funder sees the ledger read-only
- **WHEN** the current user is the budget's matching funder
- **THEN** the currency ledger section shows the balance figures and history, but not the record-receipt/record-conversion actions

#### Scenario: Funder viewing before actual_currency is set
- **WHEN** the matching funder views the ledger section and `budget.actual_currency` is unset
- **THEN** the frontend shows a passive message that the grantee hasn't set it yet, without an action to set it themselves

### Requirement: Record a funding receipt
The frontend SHALL let the budget owner record a funding receipt (an amount and a received date) against a budget via the backend's funding-receipt creation endpoint.

#### Scenario: Record a receipt
- **WHEN** the owner submits a funding receipt with an amount and a received date
- **THEN** the frontend sends a create request for that receipt and, on success, adds it to the displayed receipt history

### Requirement: Record a currency conversion
The frontend SHALL let the budget owner record a currency conversion (a donor-currency amount converted and the local-currency amount received) against a budget, without accepting or sending a separately entered exchange rate.

#### Scenario: Record a conversion
- **WHEN** the owner submits a conversion with a donor-currency amount and a local-currency amount received
- **THEN** the frontend sends a create request for that conversion (no rate field) and, on success, adds it to the displayed conversion history

### Requirement: Received-to-date summary
The frontend SHALL show the sum of a budget's recorded funding receipts as a "received to date" figure, and SHALL compare it against `Budget.total_amount` as a percentage or progress indicator only when `Budget.local_currency` equals `Budget.actual_currency`; otherwise it SHALL show the received-to-date sum and `total_amount` as two separate currency-labeled figures with no computed ratio between them.

#### Scenario: Same-currency budget shows a comparable total
- **WHEN** a budget's `local_currency` equals its `actual_currency` and it has recorded funding receipts
- **THEN** the currency ledger section shows the summed receipts against `total_amount` as a percentage or progress indicator

#### Scenario: Mismatched-currency budget shows two separate figures
- **WHEN** a budget's `local_currency` differs from its `actual_currency`
- **THEN** the currency ledger section shows "received to date" (in `actual_currency`) and the budget total (in `local_currency`) as separate labeled figures, with no computed percentage between them

### Requirement: Unconsumed balance display

> **Added 2026-07-31:** design.md originally deferred any balance figure as a Non-Goal, assuming no backend summary endpoint existed. Implementation-time research found one already does: `GET /api/v1/currency-conversions/balance/{budget_id}` (`get_ledger_balance_service`, shipped as part of backend ticket #148) returns per-currency `donor_balance`/`local_balance`, with `local_balance` already netted against report-line consumption server-side. This requirement folds that in; the FIFO/allocation-trail UI (which specific conversion funded which expense) remains out of scope — no endpoint exposes that.

The frontend SHALL show the budget's unconverted donor-currency balance and unconsumed local-currency balance, sourced from the backend's `GET /currency-conversions/balance/{budget_id}` endpoint, without any client-side re-derivation of FIFO/allocation logic.

#### Scenario: Balance figures shown
- **WHEN** the currency ledger section is visible (`actual_currency` set, current user is the owner)
- **THEN** it shows `donor_balance` (labeled with `actual_currency`) and `local_balance` (labeled with `local_currency`) from the balance endpoint, as two separate figures, never blended into one

#### Scenario: Negative local balance is shown as-is
- **WHEN** `local_balance` is negative (report-line expenses have consumed more than converted funds cover, pending a conversion that retroactively backfills it)
- **THEN** the frontend displays the negative figure as returned, without clamping or hiding it

### Requirement: Chronological ledger history display
The frontend SHALL list a budget's recorded funding receipts and currency conversions in chronological order, showing each conversion's implied rate (donor amount ÷ local amount) computed from its own two recorded values.

#### Scenario: History lists receipts and conversions
- **WHEN** a budget has recorded funding receipts and/or currency conversions
- **THEN** the currency ledger section lists them chronologically, with each conversion showing its implied rate

#### Scenario: Empty state
- **WHEN** a budget has no recorded receipts or conversions yet
- **THEN** the currency ledger section shows an empty state alongside the recording forms
