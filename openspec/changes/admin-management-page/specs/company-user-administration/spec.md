## ADDED Requirements

### Requirement: Admin can invite a new user to their own company
An `admin` SHALL be able to invite a new user into their own company by supplying at least an email address. The system SHALL create a pending account associated with the admin's `customer_id`, without requiring the invitee to self-register a company.

#### Scenario: Admin invites a teammate by email
- **WHEN** an `admin` submits an invite request with a teammate's email address
- **THEN** the system creates a pending user record scoped to the admin's `customer_id`, and the invitee receives a way to complete account setup (exact delivery mechanism: open question, see design.md)

#### Scenario: Non-admin cannot invite
- **WHEN** a `user`-role account (not `admin` or `superuser`) submits an invite request
- **THEN** the system rejects the request as unauthorized

### Requirement: Admin can remove a user from their own company
An `admin` SHALL be able to remove a user belonging to their own company. An admin SHALL NOT be able to remove a user belonging to a different company.

#### Scenario: Admin removes a teammate
- **WHEN** an `admin` requests removal of a user whose `customer_id` matches the admin's own
- **THEN** the user is removed (exact semantics — hard delete vs. soft-delete/anonymize: open question, see design.md)

#### Scenario: Admin cannot remove a user from another company
- **WHEN** an `admin` requests removal of a user whose `customer_id` does not match the admin's own
- **THEN** the system rejects the request as unauthorized (not-found or forbidden)

### Requirement: Admin can update their own company's details
An `admin` SHALL be able to update their own company's details (e.g. name, country, currency).

#### Scenario: Admin updates company name
- **WHEN** an `admin` submits an update to their own company's `name`
- **THEN** the company record is updated and the change is reflected for all users of that company

#### Scenario: Admin cannot update another company
- **WHEN** an `admin` submits an update targeting a `customer_id` other than their own
- **THEN** the system rejects the request as unauthorized
