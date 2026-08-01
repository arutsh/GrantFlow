## ADDED Requirements

### Requirement: Donor commitment and estimated rate are editable on the budget edit form
The system SHALL expose `donor_total_amount` and `estimated_exchange_rate` as editable fields on the budget edit form, disabled under the same conditions the form already disables `actual_currency` (confirmed budgets).

#### Scenario: Grantee enters the donor's stated total and their own estimated rate
- **WHEN** the budget owner opens the edit form for an unconfirmed budget with `actual_currency` set to `EUR`
- **THEN** the form shows editable `donor_total_amount` and `estimated_exchange_rate` fields alongside `actual_currency`

#### Scenario: Fields disabled on a confirmed budget
- **WHEN** the budget owner opens the edit form for a `confirmed` budget
- **THEN** the `donor_total_amount` and `estimated_exchange_rate` fields are disabled, consistent with the other locked metadata fields

### Requirement: Budget totals show the donor commitment and estimated local cap alongside the real total
Wherever a budget's total is displayed and the budget has a non-null `estimated_local_cap`, the system SHALL show the donor-currency commitment, the grantee's estimated rate, and the estimated local cap together with the real running `total_amount`, labeled as an estimate. Where `estimated_local_cap` is `null`, the system SHALL fall back to showing only the local-currency `total_amount`, unchanged from current behavior.

#### Scenario: Estimate shown alongside the real total when both inputs exist
- **WHEN** a budget with `donor_total_amount = 10000` (`EUR`), `estimated_exchange_rate = 0.8`, `estimated_local_cap = 8000`, and a real `total_amount = 6000` (`GBP`, from lines built so far) is displayed on the single-budget view
- **THEN** the view shows the €10,000 donor commitment, the estimated rate, the £8,000 estimated local cap, and the real £6,000 total_amount together, with the estimate labeled accordingly

#### Scenario: Local-only fallback when no estimate exists
- **WHEN** a budget with no `donor_total_amount` or no `estimated_exchange_rate` set is displayed
- **THEN** the view shows only `total_amount` in `local_currency`, identical to current behavior

### Requirement: Budget-lines table offers a Local/Donor/Both currency display toggle
The system SHALL provide a display toggle with three states — Local, Donor (estimated), Both — on the budget-lines table, applying to both the `Amount` and `Used` columns, converting local-currency figures to their donor-currency equivalent using the budget's `estimated_exchange_rate`. The toggle SHALL only be shown when the budget has a non-null `estimated_exchange_rate`; converted figures SHALL be visually labeled as estimated.

#### Scenario: Toggle available when an estimated rate exists
- **WHEN** the budget-lines table is rendered for a budget with a non-null `estimated_exchange_rate`
- **THEN** the Local/Donor(estimated)/Both toggle is shown above the table

#### Scenario: Toggle hidden when no estimated rate exists
- **WHEN** the budget-lines table is rendered for a budget with no `estimated_exchange_rate` set
- **THEN** the toggle is not shown and the table renders local-currency figures only, identical to current behavior

#### Scenario: Donor view converts Amount and Used using the estimated rate
- **WHEN** the toggle is set to "Donor (estimated)" for a budget line with `amount = 800` (local) and `estimated_exchange_rate = 0.8`
- **THEN** the `Amount` column shows the donor-currency equivalent (1000, in `actual_currency`), labeled as estimated, and the `Used` column's figure is converted the same way

#### Scenario: Both view shows local and donor figures together
- **WHEN** the toggle is set to "Both" for a budget line
- **THEN** the `Amount` and `Used` columns each show the local-currency figure and its donor-currency equivalent together, the latter labeled as estimated
