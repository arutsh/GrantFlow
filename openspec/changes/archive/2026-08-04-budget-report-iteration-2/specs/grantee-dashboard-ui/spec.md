## ADDED Requirements

### Requirement: Grantee dashboard displays real budget-status counts
The system SHALL replace `Dashboard.tsx`'s hardcoded mock stats with a stat card showing the count of the grantee's budgets grouped by status, sourced from the `grantee-dashboard-api` endpoint.

#### Scenario: Dashboard shows real counts, not mock data
- **WHEN** the grantee dashboard is loaded
- **THEN** the budget-status stat card reflects the grantee's actual budgets, not a hardcoded value

### Requirement: Grantee dashboard displays committed, received, and conversion-progress figures per currency
The system SHALL display, for each donor currency the grantee has confirmed budgets in, the committed total, the received total, and the conversion progress (amount and percentage), each currency shown separately and never blended with another.

#### Scenario: Multiple currencies shown as separate figures
- **WHEN** the grantee has confirmed budgets in both EUR and USD
- **THEN** the dashboard shows separate committed/received/conversion-progress figures for EUR and for USD, not one combined number

#### Scenario: Conversion progress shown as a percentage
- **WHEN** a currency's conversion progress is 50%
- **THEN** the dashboard displays that percentage alongside the converted and received amounts for that currency

### Requirement: Grantee dashboard shows a per-budget local-currency breakdown table
The system SHALL display a table with one row per confirmed budget, showing the budget's name, its funder, and its converted/spent/remaining local-currency amounts, sourced from the `grantee-dashboard-api` breakdown.

#### Scenario: Breakdown table lists every confirmed budget
- **WHEN** the grantee dashboard is loaded and the grantee has 4 confirmed budgets
- **THEN** the breakdown table shows 4 rows, one per confirmed budget, each with its own converted/spent/remaining figures

#### Scenario: Remaining column reflects each budget's earmarked share of a shared bank balance
- **WHEN** a grantee holds funds for multiple budgets in a single pooled local-currency bank account
- **THEN** each budget's row shows its own remaining local-currency figure, independent of the others, so the donor of any one budget can identify their share
