## ADDED Requirements

### Requirement: Reports nav item leads to a working cross-budget reports directory
The system SHALL route the existing "Reports" sidebar nav item to a real page listing reports across all of the user's budgets, replacing today's dead link (which falls through to a catch-all redirect to `/dashboard`).

#### Scenario: Navigating to Reports shows the directory, not a redirect
- **WHEN** a user clicks the "Reports" sidebar item
- **THEN** the system displays the reports directory page, not a redirect to `/dashboard`

### Requirement: Reports directory table includes Budget and Donor columns with a View Budget action
The system SHALL display, for each report in the directory, its name, its parent budget's name, its donor/funder, its period, and its status, plus actions to view the report and to view its parent budget.

#### Scenario: Directory row shows budget and donor
- **WHEN** the reports directory is rendered
- **THEN** each row shows the report name, its budget's name, its donor/funder, its period, and its status

#### Scenario: View Budget action navigates to the budget
- **WHEN** a user selects "View Budget" on a report row
- **THEN** the system navigates to that report's parent budget's single-budget view

### Requirement: Reports directory supports filtering by status, budget, and donor
The system SHALL provide filter controls on the reports directory for report status, budget/program, and donor, applied against the backing `report-directory-api` endpoint.

#### Scenario: Filtering by status narrows the visible rows
- **WHEN** a user selects a status filter (e.g. "Submitted")
- **THEN** only reports matching that status are shown

#### Scenario: Filtering by budget narrows the visible rows
- **WHEN** a user selects a specific budget/program from the budget filter
- **THEN** only reports belonging to that budget are shown

#### Scenario: Filtering by donor narrows the visible rows
- **WHEN** a user selects a specific donor from the donor filter
- **THEN** only reports belonging to budgets funded by that donor are shown

### Requirement: Reports directory matches the established table/mobile-card and empty-state patterns
The system SHALL render the reports directory using the same status-badge styling, mobile card fallback below the existing breakpoint, and empty-state treatment already used by the per-budget reports table.

#### Scenario: Mobile view shows cards instead of a table
- **WHEN** the reports directory is viewed at a mobile viewport width
- **THEN** the system renders the same data as stacked cards instead of a table, consistent with the existing per-budget reports page

#### Scenario: Empty state when no reports match
- **WHEN** no reports exist (or none match the active filters)
- **THEN** the system shows an empty-state message consistent with existing empty-state treatments elsewhere in the app
