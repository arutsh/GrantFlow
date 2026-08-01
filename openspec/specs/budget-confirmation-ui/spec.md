# budget-confirmation-ui Specification

## Purpose
TBD - created by syncing change budget-report-frontend. Update Purpose after archive.

## Requirements

### Requirement: Budget confirmation action
The frontend SHALL let a budget owner, or the customer matching the budget's `funding_customer_id`, set a `start_date` and transition a `draft` or `ai_draft` budget to `confirmed`, using the existing `PATCH /budgets/{id}` endpoint. The backend SHALL authorize this specific transition (status `confirmed` with `start_date` set, from `draft`/`ai_draft`) for either party; all other budget mutations remain owner-only.

#### Scenario: Confirm action visible on an unconfirmed budget
- **WHEN** the current user owns a budget whose `status` is `draft` or `ai_draft`
- **THEN** the single-budget view shows a "Confirm Budget" action with a `start_date` picker

#### Scenario: Confirm action visible to the matching funder
- **WHEN** the current user's `customer_id` matches the budget's `funding_customer_id`, and the budget's `status` is `draft` or `ai_draft`
- **THEN** the single-budget view shows the same "Confirm Budget" action, and the backend accepts the resulting `PATCH` from that customer

#### Scenario: Confirm action hidden once confirmed
- **WHEN** a budget's `status` is `confirmed` or `archived`
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

### Requirement: Budget status and dates are visible on the single-budget view
The frontend SHALL display the budget's `status`, `start_date` (when set), and a computed end date (`start_date + duration_months`, computed client-side since no backend `end_date` field exists) on the single-budget view, outside of edit mode.

#### Scenario: Status and dates shown once available
- **WHEN** viewing a budget whose `start_date` is set
- **THEN** the view shows the budget's status label, its start date, and a computed end date derived from `start_date` and `duration_months`

#### Scenario: Dates omitted before confirmation
- **WHEN** viewing a `draft`/`ai_draft` budget with no `start_date` set
- **THEN** the view shows the status label but omits start/end dates rather than showing empty or fabricated values

### Requirement: Reverting a confirmed budget to draft
The frontend SHALL let the budget owner revert a `confirmed` budget back to `draft` ("Cancel Confirmation"). The backend SHALL reject this transition if the budget has any report in a non-draft state (`submitted`, `approved`, `rejected`), and SHALL delete any draft-state report(s) belonging to the budget as part of a successful transition.

#### Scenario: Revert action visible to the owner only
- **WHEN** the current user owns a `confirmed` budget
- **THEN** the single-budget view shows a "Cancel Confirmation" action; a matching funder who is not the owner does not see this action

#### Scenario: Revert blocked by a non-draft report
- **WHEN** the owner triggers "Cancel Confirmation" on a budget that has a `submitted`, `approved`, or `rejected` report
- **THEN** the backend rejects the transition and the frontend shows an explanatory error, leaving the budget `confirmed`

#### Scenario: Revert succeeds and clears draft reports
- **WHEN** the owner triggers "Cancel Confirmation" on a budget whose reports (if any) are all `draft`
- **THEN** the backend transitions the budget to `draft`, deletes its draft report(s), and the frontend reflects the budget as `draft` with no `start_date`

### Requirement: Editing is blocked once a budget is confirmed
The frontend SHALL hide/disable the budget's "Edit" action once `Budget.status === "confirmed"`, and the backend SHALL reject direct attempts to modify budget metadata or lines in that state. This is gated on confirmation, not on report existence — a report can only exist on an already-confirmed budget, so confirmed status is the broader and correct condition.

> **Amended 2026-08-01**: `actual_currency` is a narrow, deliberate exception to this lock — see `specs/budget-currency-ledger-ui/spec.md`. The currency-ledger's "set actual currency" action only ever runs on an already-confirmed budget, so a PATCH containing only `actual_currency` is allowed through even while `isLocked`; a PATCH bundling `actual_currency` with any other still-locked field (name, duration, funder, lines) is rejected exactly as before. This surfaced as a real bug during dogfooding: the ledger's own setup flow was rejected by this same lock before the carve-out existed.

#### Scenario: Edit action hidden once confirmed, even before any report exists
- **WHEN** a budget's `status` is `confirmed`, regardless of whether it has any report yet
- **THEN** the single-budget view hides or disables the "Edit" action, with an explanatory message, and a direct edit attempt is rejected by the backend

#### Scenario: Backend rejects a direct edit attempt
- **WHEN** a budget line or metadata update request is sent for a budget whose `status` is `confirmed`, regardless of whether it has any report yet
- **THEN** the backend rejects the request rather than applying it

#### Scenario: actual_currency alone is allowed through the lock
- **WHEN** a confirmed budget receives a PATCH containing only `actual_currency`
- **THEN** the backend applies it rather than rejecting it as a locked metadata edit

#### Scenario: actual_currency bundled with another locked field is still rejected
- **WHEN** a confirmed budget receives a PATCH containing `actual_currency` together with another metadata field (e.g. `name`)
- **THEN** the backend rejects the entire request
