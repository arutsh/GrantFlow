## ADDED Requirements

### Requirement: Actual currency required before ledger use
The frontend SHALL require `Budget.actual_currency` to be set before showing the funding-receipt/currency-conversion recording forms, since a receipt is denominated in that currency, and SHALL let the budget owner set it via the existing budget-edit form.

#### Scenario: Ledger prompts for actual currency when unset
- **WHEN** the budget owner opens the currency ledger section on a budget with no `actual_currency` set
- **THEN** the frontend shows a prompt to set the actual currency (linking into the budget-edit form) instead of the recording forms

#### Scenario: Ledger forms available once actual currency is set
- **WHEN** `budget.actual_currency` is set
- **THEN** the currency ledger section shows the funding-receipt and currency-conversion recording forms

### Requirement: Currency ledger section is owner-only
The frontend SHALL show the currency ledger section only to the budget owner, matching the backend's owner-scoped routes.

#### Scenario: Non-owner does not see the ledger section
- **WHEN** the current user is not the budget's owner (e.g. the funder, or an unrelated viewer)
- **THEN** the single-budget view does not show the currency ledger section

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

### Requirement: Chronological ledger history display
The frontend SHALL list a budget's recorded funding receipts and currency conversions in chronological order, showing each conversion's implied rate (donor amount ÷ local amount) computed from its own two recorded values.

#### Scenario: History lists receipts and conversions
- **WHEN** a budget has recorded funding receipts and/or currency conversions
- **THEN** the currency ledger section lists them chronologically, with each conversion showing its implied rate

#### Scenario: Empty state
- **WHEN** a budget has no recorded receipts or conversions yet
- **THEN** the currency ledger section shows an empty state alongside the recording forms
