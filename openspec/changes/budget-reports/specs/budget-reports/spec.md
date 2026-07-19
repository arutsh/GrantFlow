## ADDED Requirements

### Requirement: Report creation against a Budget
The system SHALL allow a user with access to a `Budget` to create a `Report` against it, with a name and optional reporting period (`period_start`/`period_end`), starting in `draft` status.

#### Scenario: Grantee creates a draft report
- **WHEN** the budget owner creates a report with a name for their budget
- **THEN** the system creates a `Report` record with `status = draft`, linked to that budget

#### Scenario: Cannot create a report against a budget the user cannot access
- **WHEN** a user without owner/funder access to the target budget attempts to create a report against it
- **THEN** the system rejects the request with a permission error

### Requirement: Report lines reference a specific budget line
The system SHALL allow report lines to be added to a `draft` report, each referencing exactly one `BudgetLine` belonging to the same `Budget` as the report, with a description, amount, and optional structured metadata.

#### Scenario: Add a report line against a budget line
- **WHEN** the report owner adds a report line specifying a `budget_line_id` that belongs to the report's budget, with a description and amount
- **THEN** the system creates a `ReportLine` linked to that report and budget line

#### Scenario: Reject a budget line from a different budget
- **WHEN** a report line is created referencing a `budget_line_id` that belongs to a different budget than the report's budget
- **THEN** the system rejects the request

#### Scenario: Multiple report lines against the same budget line
- **WHEN** two report lines are created referencing the same `budget_line_id` on the same draft report
- **THEN** both report lines are created successfully, each independently trackable

### Requirement: Report status workflow
The system SHALL enforce a report status lifecycle of `draft → submitted → approved` or `draft → submitted → rejected`, with `rejected → draft` allowed to reopen the report, and no other transitions permitted.

#### Scenario: Submit a draft report
- **WHEN** the report owner submits a report currently in `draft` status
- **THEN** the report transitions to `submitted` and `submitted_at` is recorded

#### Scenario: Cannot re-submit a non-draft report
- **WHEN** a submit action is attempted on a report that is not in `draft` status
- **THEN** the system rejects the request

#### Scenario: Funder approves a submitted report
- **WHEN** the user matching the budget's `funding_customer_id` approves a report currently in `submitted` status
- **THEN** the report transitions to `approved`, and `reviewed_at`/`reviewed_by` are recorded

#### Scenario: Funder rejects a submitted report with notes
- **WHEN** the user matching the budget's `funding_customer_id` rejects a report currently in `submitted` status, optionally including review notes
- **THEN** the report transitions to `rejected`, `reviewed_at`/`reviewed_by`/`review_notes` are recorded

#### Scenario: Non-funder cannot review a report
- **WHEN** a user who is not the budget's funder attempts to approve or reject a submitted report
- **THEN** the system rejects the request with a permission error

#### Scenario: Rejected report reopens to draft
- **WHEN** the report owner transitions a `rejected` report back to `draft`
- **THEN** the report's status becomes `draft` and its lines become editable again

### Requirement: Report lines lock outside of draft status
The system SHALL prevent creating, updating, or deleting report lines (and their attachments) on a report whose status is not `draft`.

#### Scenario: Cannot add a line to a submitted report
- **WHEN** a user attempts to add a report line to a report in `submitted`, `approved`, or `rejected` status
- **THEN** the system rejects the request

#### Scenario: Cannot edit a line on a submitted report
- **WHEN** a user attempts to update an existing report line on a report that is not in `draft` status
- **THEN** the system rejects the request

### Requirement: Report and report-line retrieval
The system SHALL allow listing and retrieving reports (with their lines) and report lines, scoped to users with access to the underlying budget.

#### Scenario: List reports for a budget
- **WHEN** a user with access to a budget requests its reports
- **THEN** the system returns all reports linked to that budget

#### Scenario: Retrieve a single report with its lines
- **WHEN** a user with access requests a specific report by id
- **THEN** the system returns the report including its associated report lines
