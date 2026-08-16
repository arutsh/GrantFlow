## ADDED Requirements

### Requirement: Restore action on archived budget cards
A budget card whose status is `archived` SHALL show a "Restore" action, visible only to the budget's owner, instead of the Edit/Delete actions shown on active-status cards.

#### Scenario: Owner views an archived budget card
- **WHEN** the current user owns a budget whose `status` is `archived`
- **THEN** the card shows a "Restore" action and does not show Edit or Delete

#### Scenario: Non-owner views an archived budget card
- **WHEN** the current user does not own an `archived` budget they can otherwise view (e.g. a matching funder)
- **THEN** the card does not show a "Restore" action

#### Scenario: Restoring a budget
- **WHEN** the owner taps "Restore" on an archived budget card
- **THEN** the frontend calls `POST /budgets/{id}/restore`, and on success the card reflects the budget's new status (`confirmed` or `draft`) with its normal active-status actions

#### Scenario: Restore request fails
- **WHEN** the `POST /budgets/{id}/restore` request fails
- **THEN** the frontend shows an error message and the card remains `archived`
