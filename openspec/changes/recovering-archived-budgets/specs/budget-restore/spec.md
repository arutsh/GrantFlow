## ADDED Requirements

### Requirement: Restoring an archived budget
The backend SHALL provide `POST /budgets/{id}/restore`, callable only by the budget's owner (or a superuser), which transitions a budget whose `status` is `archived` back to an active status. The target status is derived by the server, not supplied by the caller: `confirmed` if the budget's `confirmed_at` is set and its `start_date` is still set, otherwise `draft`.

#### Scenario: Restoring a budget that was confirmed before archiving
- **WHEN** the owner calls `POST /budgets/{id}/restore` on a budget whose `status` is `archived`, `confirmed_at` is set, and `start_date` is set
- **THEN** the backend sets `status` to `confirmed`, leaves `confirmed_at` and `start_date` unchanged, and returns the updated budget

#### Scenario: Restoring a budget that was never confirmed before archiving
- **WHEN** the owner calls `POST /budgets/{id}/restore` on a budget whose `status` is `archived` and `confirmed_at` is not set
- **THEN** the backend sets `status` to `draft` and returns the updated budget

#### Scenario: Restoring falls back to draft if start_date is missing despite a prior confirmation
- **WHEN** the owner calls `POST /budgets/{id}/restore` on a budget whose `status` is `archived`, `confirmed_at` is set, but `start_date` is not set
- **THEN** the backend sets `status` to `draft` rather than `confirmed`

#### Scenario: Restore is rejected on a non-archived budget
- **WHEN** `POST /budgets/{id}/restore` is called on a budget whose `status` is not `archived`
- **THEN** the backend rejects the request and the budget's status is unchanged

#### Scenario: Restore is rejected for a non-owner
- **WHEN** a user who is neither the budget's owner nor a superuser calls `POST /budgets/{id}/restore`
- **THEN** the backend rejects the request with the same not-found response used elsewhere for unauthorized access to a budget
