## MODIFIED Requirements

### Requirement: Donor Dashboard Page
The system SHALL provide a donor dashboard page displaying the donor's total budgets, total allocated amount, grantee directory, and funded-budgets list, with a "View Reports" action per budget that is disabled and mocked pending the separate report-review feature. At viewport widths below `sm` (640px), the grantee directory SHALL render as a horizontally scrolling row of cards and the funded-budgets list SHALL render as a vertical list of compact rows (name, grantee, amount, status) instead of the table used at `sm` and above.

#### Scenario: Donor views their dashboard
- **WHEN** an authenticated donor navigates to the donor dashboard page
- **THEN** the page SHALL display stat tiles for total budgets and total allocated, a list of grantees, and a table of funded budgets

#### Scenario: Donor views their dashboard on a narrow viewport
- **WHEN** an authenticated donor navigates to the donor dashboard page at a viewport width below 640px
- **THEN** the page SHALL display stat tiles for total budgets and total allocated, grantees as a horizontally scrolling row of cards, and funded budgets as a vertical list of compact rows rather than a table

#### Scenario: View Reports is not yet functional
- **WHEN** the donor dashboard renders a funded budget row
- **THEN** its "View Reports" button SHALL be rendered disabled and SHALL display a tooltip indicating the feature is coming soon, and SHALL NOT display fabricated report data

#### Scenario: Donor with no funded budgets views the dashboard
- **WHEN** an authenticated donor with `is_donor = true` but zero funded budgets views the page
- **THEN** the page SHALL show an empty/no-data state instead of an error or blank screen
