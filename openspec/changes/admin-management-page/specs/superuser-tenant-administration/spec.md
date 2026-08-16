## ADDED Requirements

### Requirement: Superuser can delete or update any user
A `superuser` SHALL be able to delete or update any user, regardless of which company the user belongs to.

#### Scenario: Superuser deletes a user in any company
- **WHEN** a `superuser` requests deletion of a user belonging to any `customer_id`
- **THEN** the user is removed, subject to the same delete semantics as `company-user-administration` (open question, see design.md)

#### Scenario: Superuser updates a user in any company
- **WHEN** a `superuser` requests an update (e.g. role, status) to a user belonging to any `customer_id`
- **THEN** the update is applied

### Requirement: Superuser can delete or update any company
A `superuser` SHALL be able to delete or update any company's details.

#### Scenario: Superuser updates any company's details
- **WHEN** a `superuser` submits an update to any company's details
- **THEN** the company record is updated

#### Scenario: Superuser deletes a company
- **WHEN** a `superuser` requests deletion of a company
- **THEN** the company is removed, subject to open questions on cascading effects across services (see design.md)

### Requirement: Superuser tenant administration mechanism is undecided
Whether superuser access under this capability is implemented as dedicated superuser-scoped endpoints, or as the superuser using the `company-user-administration` endpoints under an impersonation session (per the in-progress `superuser-cross-tenant-access` change), SHALL be decided before implementation.

#### Scenario: Placeholder pending design decision
- **WHEN** implementation of this capability begins
- **THEN** the mechanism decision in design.md's Open Questions SHALL be resolved first
