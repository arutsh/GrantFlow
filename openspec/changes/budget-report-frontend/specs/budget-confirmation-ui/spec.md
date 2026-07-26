## ADDED Requirements

### Requirement: Budget confirmation action
The frontend SHALL let a budget owner set a `start_date` and transition a `draft` or `ai_draft` budget to `confirmed`, using the existing `PATCH /budgets/{id}` endpoint.

#### Scenario: Confirm action visible on an unconfirmed budget
- **WHEN** the current user owns a budget whose `status` is `draft` or `ai_draft`
- **THEN** the single-budget view shows a "Confirm Budget" action with a `start_date` picker

#### Scenario: Confirm action hidden once confirmed
- **WHEN** a budget's `status` is `confirmed`, `submitted`, or `archived`
- **THEN** the single-budget view does not show the "Confirm Budget" action

#### Scenario: Confirming without a start date is blocked client-side
- **WHEN** the user opens the confirmation action and has not yet picked a `start_date`
- **THEN** the "Confirm Budget" button is disabled

#### Scenario: Successful confirmation
- **WHEN** the user picks a `start_date` and clicks "Confirm Budget"
- **THEN** the frontend sends `PATCH /budgets/{id}` with `start_date` and `status: "confirmed"`, and on success updates the displayed budget status and hides the confirmation action

#### Scenario: Backend rejects confirmation
- **WHEN** the `PATCH /budgets/{id}` confirmation request fails (e.g. the backend rejects the transition)
- **THEN** the frontend shows an error message and leaves the budget in its prior displayed status, without hiding the confirmation action

### Requirement: Confirmed status unlocks reporting
The frontend SHALL treat `Budget.status === "confirmed"` as the signal that report creation is available for that budget, matching the backend's `create_report_service` precondition.

#### Scenario: Reports section appears once confirmed
- **WHEN** a budget's `status` becomes `confirmed`
- **THEN** the single-budget view renders the Reports section with a "New Report" action available
