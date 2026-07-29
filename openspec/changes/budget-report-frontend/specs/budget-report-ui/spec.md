## ADDED Requirements

### Requirement: Report list on a budget
The frontend SHALL list all reports for a confirmed budget (or a budget with existing reports), showing each report's name, period, and status, sourced from `GET /reports/by-budget/{budget_id}`.

#### Scenario: Reports section shows existing reports
- **WHEN** a budget has one or more reports
- **THEN** the single-budget view lists each report's name, `period_start`–`period_end`, and status

#### Scenario: Empty state
- **WHEN** a confirmed budget has no reports yet
- **THEN** the Reports section shows an empty state and a "New Report" action

### Requirement: Report creation
The frontend SHALL let a budget owner create a new report against a confirmed budget via `POST /reports/`, optionally specifying a period, and SHALL surface a backend validation error (e.g. overlapping period, non-confirmed budget) inline without navigating away.

#### Scenario: Create report with default period
- **WHEN** the owner submits "New Report" without specifying a period
- **THEN** the frontend sends `POST /reports/` with only `budget_id` and `name`, and on success navigates to the new report's detail view

#### Scenario: Create report with explicit period
- **WHEN** the owner supplies both a start and end date for the new report
- **THEN** the frontend includes `period_start` and `period_end` in the `POST /reports/` request

#### Scenario: Overlapping period rejected
- **WHEN** the backend rejects report creation because the requested period overlaps an existing report
- **THEN** the frontend shows the returned error message and keeps the creation form open with the entered values intact

### Requirement: Report detail view
The frontend SHALL provide a report detail view, reachable at a dedicated route, showing the report's metadata, status, and its report lines (via `GET /reports/{id}` and `GET /report-lines/by-report/{report_id}`).

#### Scenario: Navigating to a report
- **WHEN** the user clicks a report in the Reports list
- **THEN** the frontend navigates to that report's detail route and loads its lines

### Requirement: Report line CRUD while draft
The frontend SHALL let the report owner add, edit, and delete report lines (each tied to one budget line, with a description, amount, and expense date) while the parent report's status is `draft`, and SHALL disable these actions once the report leaves `draft`.

> **Amended 2026-07-29:** added `expense_date` — the real-world date the expense happened, distinct from `created_at` — as a required field on the add-line form and an editable field on each row, following the same addition on the backend (`budget-reports` spec's "Report lines reference a specific budget line" requirement, amended the same day). The date input's `min`/`max` are clamped to the report's own `period_start`/`period_end` as a client-side UX nicety; the backend remains the authoritative validation, same pattern as the existing upload-size/content-type duplication documented in design.md.

> **Amended 2026-07-29:** added `extra_fields` (arbitrary key/value structured metadata), matching `BudgetLine`'s existing extra-fields UX (`AddBudgetLine.tsx`/`BudgetViewLinesTable.tsx`) rather than inventing a new pattern. Keys already used by any of the report's other lines are shown as dynamic table columns and are prefilled/locked (not renameable, only their value is editable) on the add-line form, so a report's lines stay comparable in one table; brand-new keys can still be added freely. Editing `extra_fields` on an *existing* line (via `ReportLineRow`'s inline edit) is out of scope for this amendment — only display and add-time entry, matching what was actually requested.

#### Scenario: Add a report line
- **WHEN** the report is `draft` and the owner submits a new line (budget line, description, amount, expense date, optional extra fields)
- **THEN** the frontend sends `POST /report-lines/` and appends the created line to the displayed list

#### Scenario: Edit/delete disabled outside draft
- **WHEN** the report's status is `submitted`, `approved`, or `rejected`
- **THEN** the frontend disables add/edit/delete controls for that report's lines

#### Scenario: Extra fields are visible as dynamic columns
- **WHEN** one or more of a report's lines have `extra_fields` set
- **THEN** the report lines table shows one column per distinct key in use, alongside the fixed budget-line/description/expense-date/amount columns

#### Scenario: Existing extra field keys are prefilled and locked on the add-line form
- **WHEN** the owner opens the "New Line" form for a report that already has lines using one or more `extra_fields` keys
- **THEN** those keys appear prefilled with an empty value and their key input is locked, while a new, unlocked key/value row can still be added

### Requirement: Report submission
The frontend SHALL let the report owner submit a `draft` report via `POST /reports/{id}/submit`, transitioning it to `submitted` and locking its lines from further edits.

#### Scenario: Submit a draft report
- **WHEN** the owner clicks "Submit" on a `draft` report
- **THEN** the frontend calls `POST /reports/{id}/submit` and, on success, updates the displayed status to `submitted` and disables line edit/delete controls

### Requirement: Report review
The frontend SHALL let an authorized reviewer (the funder identified by `budget.funding_customer_id`, or the budget owner when no funder is set) approve or reject a `submitted` report via `POST /reports/{id}/review`, and SHALL hide the review action from users who are neither the funder nor the fallback owner.

#### Scenario: Reviewer sees review action
- **WHEN** the current user's `customer_id` matches `budget.funding_customer_id` and the report status is `submitted`
- **THEN** the report detail view shows "Approve" and "Reject" actions with an optional review-notes field

#### Scenario: Non-reviewer does not see review action
- **WHEN** the current user is neither the matching funder nor the fallback owner (when no funder is set)
- **THEN** the report detail view does not show "Approve"/"Reject" actions

#### Scenario: Approve a submitted report
- **WHEN** the reviewer clicks "Approve"
- **THEN** the frontend calls `POST /reports/{id}/review` with `decision: "approved"` and updates the displayed status on success

#### Scenario: Reject a submitted report
- **WHEN** the reviewer clicks "Reject" with review notes
- **THEN** the frontend calls `POST /reports/{id}/review` with `decision: "rejected"` and the entered `review_notes`, and updates the displayed status on success

### Requirement: Reopening a rejected report
The frontend SHALL let the report owner reopen a `rejected` report via `POST /reports/{id}/reopen`, transitioning it back to `draft` and re-enabling line edits.

#### Scenario: Reopen a rejected report
- **WHEN** the owner clicks "Reopen" on a `rejected` report
- **THEN** the frontend calls `POST /reports/{id}/reopen` and, on success, updates the displayed status to `draft` and re-enables line edit/delete controls

### Requirement: Funder access to reports from the donor dashboard
The frontend SHALL let a funder reach the report list for any budget they fund from the `DonorDashboard`'s "View Reports" entry point.

#### Scenario: View Reports from donor dashboard
- **WHEN** a funder clicks "View Reports" for a funded budget on the `DonorDashboard`
- **THEN** the frontend navigates to that budget's report list
