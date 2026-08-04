## ADDED Requirements

### Requirement: List reports across all of a user's budgets
The system SHALL provide an endpoint that lists `Report`s across every budget the requesting user has access to (all budgets they own, or — for a donor — all budgets they fund), rather than requiring a single `budget_id`, mirroring the existing owner-vs-donor scoping split already used for `GET /budgets/` vs `GET /budgets/funded/`.

#### Scenario: Owner lists reports across all their budgets
- **WHEN** a budget owner with three budgets, each having at least one report, requests the reports directory without specifying a `budget_id`
- **THEN** the system returns every report belonging to any of that owner's budgets

#### Scenario: Donor lists reports across all budgets they fund
- **WHEN** a donor customer requests the reports directory
- **THEN** the system returns every report belonging to any budget where `funding_customer_id` matches that donor

#### Scenario: A budget_id filter narrows to one budget
- **WHEN** a user requests the reports directory with a `budget_id` query parameter
- **THEN** the system returns only reports belonging to that budget, still subject to the same access check as before

### Requirement: Reports directory supports status, budget, and donor filters
The system SHALL allow the reports-directory endpoint to be filtered by report `status`, `budget_id`, and (for owners) `funding_customer_id`, combinable with one another.

#### Scenario: Filter by status
- **WHEN** a user requests the reports directory with `status=submitted`
- **THEN** the system returns only reports currently in `submitted` status, across all budgets otherwise visible to them

#### Scenario: Filter by donor
- **WHEN** a budget owner requests the reports directory with `funding_customer_id` set to one of their donors
- **THEN** the system returns only reports belonging to budgets funded by that donor

#### Scenario: Combined filters
- **WHEN** a user requests the reports directory with both `status` and `budget_id` set
- **THEN** the system returns only reports matching both conditions

### Requirement: Reports directory includes budget and funder details per report
The system SHALL include each report's parent budget's `name`, `status`, and funder (`funding_customer_id`/`external_funder_name`) in the reports-directory response, without requiring a separate lookup per report.

#### Scenario: Budget and funder details present on each row
- **WHEN** the reports directory is retrieved
- **THEN** each returned report includes its budget's name, status, and funder information alongside the report's own fields
