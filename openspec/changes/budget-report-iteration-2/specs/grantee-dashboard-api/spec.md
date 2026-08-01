## ADDED Requirements

### Requirement: Dashboard reports budget counts by status
The system SHALL provide an endpoint that returns, for the authenticated grantee, the count of their budgets grouped by `status` (`draft`, `ai_draft`, `confirmed`, `archived`).

#### Scenario: Counts reflect all of the grantee's budgets regardless of status
- **WHEN** a grantee with 5 budgets — 1 `archived`, 4 `confirmed` — requests the dashboard summary
- **THEN** the response includes a count of 1 for `archived` and 4 for `confirmed`

### Requirement: Dashboard reports committed totals per donor currency, derived from real budget totals
The system SHALL compute, for each of the grantee's `confirmed` budgets that has both `actual_currency` and `estimated_exchange_rate` set, a committed figure as `total_amount ÷ estimated_exchange_rate` (converting the real, derived local total back into the donor's currency), and SHALL sum these per `actual_currency` across all such confirmed budgets, never blending currencies into one total. Confirmed budgets missing `actual_currency` or `estimated_exchange_rate` SHALL be excluded from this figure.

#### Scenario: Committed total reflects the real built budget, not the donor's promise
- **WHEN** a confirmed budget has `donor_total_amount = 10000` (EUR), `estimated_exchange_rate = 0.8`, and a real `total_amount = 7876.8` (GBP, from its actual lines)
- **THEN** that budget contributes `9846` (EUR) to the committed total, not `10000`

#### Scenario: Committed totals grouped by currency across multiple budgets
- **WHEN** a grantee has one confirmed budget contributing 9846 EUR and another contributing 35000 USD to the committed figure
- **THEN** the response reports `9846 EUR` and `35000 USD` as separate figures, never summed together

#### Scenario: Confirmed budget without a usable rate is excluded
- **WHEN** a confirmed budget has no `actual_currency` or no `estimated_exchange_rate` set
- **THEN** that budget contributes nothing to the committed-by-currency figures (it is not folded into any other currency's total)

### Requirement: Dashboard reports received totals per donor currency
The system SHALL sum `FundingReceipt.amount` across the grantee's `confirmed` budgets, grouped by each budget's `actual_currency`, never blending currencies into one total.

#### Scenario: Received totals grouped by currency
- **WHEN** funding receipts across confirmed budgets total 20000 EUR and 15000 USD
- **THEN** the response reports `20000 EUR` and `15000 USD` as separate figures

### Requirement: Dashboard reports conversion progress per donor currency
The system SHALL compute, per donor currency, the sum of `CurrencyConversion.donor_amount` across the grantee's `confirmed` budgets, alongside that currency's received total, and SHALL express conversion progress as both an amount and a percentage of the received total for that currency.

#### Scenario: Conversion progress shown per currency
- **WHEN** a grantee has received 20000 EUR total and converted 10000 EUR of it
- **THEN** the response reports, for EUR, a converted amount of 10000 and a conversion percentage of 50%

#### Scenario: Different currencies show independent progress
- **WHEN** a grantee has converted 50% of their received EUR and 30% of their received USD
- **THEN** the response reports these two percentages independently, without averaging or combining them

### Requirement: Dashboard provides a per-budget local-currency breakdown
The system SHALL provide, for each of the grantee's `confirmed` budgets, its name, its funder, its converted-to-local-currency amount, its consumed (spent) local-currency amount, and its remaining (unconsumed) local-currency amount, reusing the existing per-budget ledger-balance computation rather than a new allocation algorithm.

#### Scenario: Breakdown row reflects one budget's ledger position
- **WHEN** a confirmed budget has had 8000 GBP converted to local currency and 3000 GBP consumed by report-line expenses
- **THEN** its breakdown row shows 8000 GBP converted, 3000 GBP spent, and 5000 GBP remaining

#### Scenario: Breakdown covers every confirmed budget
- **WHEN** the grantee has 4 confirmed budgets
- **THEN** the breakdown includes one row per confirmed budget, each independently computed
