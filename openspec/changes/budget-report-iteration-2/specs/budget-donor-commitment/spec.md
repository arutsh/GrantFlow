## ADDED Requirements

### Requirement: Record a donor's stated total commitment
The system SHALL allow a budget owner to record `donor_total_amount`, a directly-entered figure denominated in the budget's `actual_currency`, representing the donor's stated commitment for that budget, separate from `total_amount` (which remains the derived sum of budget-line amounts in `local_currency`).

#### Scenario: Set the donor commitment on an unconfirmed budget
- **WHEN** the budget owner sets `donor_total_amount` to 10000 on a `draft` or `ai_draft` budget whose `actual_currency` is `EUR`
- **THEN** the system stores `donor_total_amount = 10000` on that budget, unrelated to and without altering `total_amount`

#### Scenario: Donor commitment is optional
- **WHEN** a budget is created or edited without specifying `donor_total_amount`
- **THEN** the system leaves `donor_total_amount` unset and all other behavior is unaffected

### Requirement: Grantee enters and stores their own estimated exchange rate
The system SHALL allow a budget owner to directly enter `estimated_exchange_rate` (`actual_currency` → `local_currency`), a value the grantee chooses themselves to guide budget-line construction, and SHALL persist it immediately so it survives the grantee saving a partially-built draft and returning to it later. The system SHALL NOT derive this value from `total_amount`/`donor_total_amount` or any other computation.

#### Scenario: Grantee sets an estimated rate before building lines
- **WHEN** the budget owner sets `estimated_exchange_rate` to 0.8 on a `draft` budget with `donor_total_amount = 10000` and no budget lines yet
- **THEN** the system stores `estimated_exchange_rate = 0.8` on that budget

#### Scenario: Estimated rate survives a paused draft
- **WHEN** a budget owner sets `estimated_exchange_rate`, adds some but not all intended budget lines, and returns to the budget in a later session
- **THEN** the previously-entered `estimated_exchange_rate` is still present, unaffected by the number of lines added so far

#### Scenario: Estimated rate is optional
- **WHEN** a budget is created or edited without specifying `estimated_exchange_rate`
- **THEN** the system leaves `estimated_exchange_rate` unset and all other behavior is unaffected

### Requirement: Estimated local cap is derived, never stored
The system SHALL compute an `estimated_local_cap` (in `local_currency`) as `donor_total_amount × estimated_exchange_rate` at read time whenever a budget is returned, and SHALL NOT persist this figure as its own field.

#### Scenario: Estimated local cap present when both inputs are set
- **WHEN** a budget with `donor_total_amount = 10000` and `estimated_exchange_rate = 0.8` is retrieved
- **THEN** the response includes `estimated_local_cap = 8000`

#### Scenario: Estimated local cap is null when either input is unset
- **WHEN** a budget with `donor_total_amount` set but no `estimated_exchange_rate` (or vice versa) is retrieved
- **THEN** the response's `estimated_local_cap` is `null`

### Requirement: Donor commitment and estimated rate are locked once the budget is confirmed
The system SHALL treat `donor_total_amount` and `estimated_exchange_rate` as budget metadata subject to the same edit lock as other metadata fields (`local_currency`, `actual_currency`, etc.): editable only while the budget's status is not `confirmed`.

#### Scenario: Cannot change donor commitment or estimated rate on a confirmed budget
- **WHEN** a user attempts to update `donor_total_amount` or `estimated_exchange_rate` on a budget whose status is `confirmed`
- **THEN** the system rejects the request, consistent with how other metadata edits are rejected on confirmed budgets

#### Scenario: Both fields editable before confirmation
- **WHEN** the budget owner updates `donor_total_amount` and/or `estimated_exchange_rate` on a budget whose status is `draft` or `ai_draft`
- **THEN** the system accepts and persists the change

### Requirement: Budget records when it was most recently confirmed
The system SHALL set `confirmed_at` to the current time whenever a budget's status transitions to `confirmed`, and SHALL update it again to a fresh value if the budget is later reverted to `draft` and confirmed again, so it always reflects the most recent confirmation rather than the first.

#### Scenario: Confirming a budget sets confirmed_at
- **WHEN** a `draft` budget transitions to `confirmed`
- **THEN** the system sets `confirmed_at` to the time of that transition

#### Scenario: Re-confirming after a revert updates confirmed_at
- **WHEN** a `confirmed` budget is reverted to `draft` and later confirmed again
- **THEN** `confirmed_at` reflects the time of the second confirmation, not the first

#### Scenario: Unconfirmed budgets have no confirmed_at
- **WHEN** a `draft` or `ai_draft` budget that has never been confirmed is retrieved
- **THEN** the response's `confirmed_at` is `null`
