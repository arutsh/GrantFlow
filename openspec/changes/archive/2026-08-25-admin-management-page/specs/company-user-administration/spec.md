## ADDED Requirements

### Requirement: Admin can invite a new user to their own company
An `admin` SHALL be able to invite a new user into their own company by supplying at least an email address. The system SHALL create a pending user record with `customer_id` set to the admin's own, `hashed_password` unset, and generate a single-use, expiring accept-invite token (reusing the `email_verification_token_hash`/`email_verification_expires_at` mechanism), without requiring the invitee to self-register a company.

#### Scenario: Admin invites a teammate by email
- **WHEN** an `admin` submits an invite request with a teammate's email address
- **THEN** the system creates a pending user record scoped to the admin's `customer_id`, generates an accept-invite token, and the invitee receives a link to complete account setup

#### Scenario: Non-admin cannot invite
- **WHEN** a `user`-role account (not `admin` or `superuser`) submits an invite request
- **THEN** the system rejects the request as unauthorized

#### Scenario: Invited user appears in the company's user list before accepting
- **WHEN** an admin views their company's user list after inviting a teammate who has not yet accepted
- **THEN** the invited user appears with `pending` status

### Requirement: Invited user accepts their invitation and sets a password
The system SHALL provide an endpoint where an invited user submits their accept-invite token along with a chosen password, and on success sets `hashed_password`, marks `email_verified = true`, and clears the token so it cannot be reused.

#### Scenario: Valid accept-invite token sets the password
- **WHEN** an invited user submits a valid, unexpired accept-invite token with a new password
- **THEN** the system sets `hashed_password` from the submitted password, sets `email_verified = true`, and clears the stored token

#### Scenario: Expired or already-used token is rejected
- **WHEN** an invited user submits an accept-invite token that is expired or no longer matches a stored token
- **THEN** the request is rejected and no password is set

### Requirement: Admin can remove a user from their own company
An `admin` SHALL be able to remove a user belonging to their own company. Removal SHALL follow the same soft-delete/anonymization path as GDPR self-service erasure: personal identifiers are tombstoned, `deletion_requested_at`/`deleted_at` are set, and the user's active sessions are revoked. An admin SHALL NOT be able to remove a user belonging to a different company. Removal SHALL be rejected if it would leave the company with zero users holding the `admin` role.

#### Scenario: Admin removes a teammate
- **WHEN** an `admin` requests removal of a non-admin user whose `customer_id` matches the admin's own
- **THEN** the user's name/email are tombstoned, `deleted_at` is set, and their sessions are revoked

#### Scenario: Admin removes another admin
- **WHEN** an `admin` requests removal of a different `admin`-role user in the same company, and at least one other admin remains after the removal
- **THEN** the removal succeeds using the same soft-delete path

#### Scenario: Admin cannot remove a user from another company
- **WHEN** an `admin` requests removal of a user whose `customer_id` does not match the admin's own
- **THEN** the system rejects the request as unauthorized (not-found or forbidden)

#### Scenario: Removing the last admin is rejected
- **WHEN** an `admin` requests removal of the only remaining `admin`-role user in their company (including themselves)
- **THEN** the system rejects the request and the user is not removed

### Requirement: Admin can promote or demote a user's role within their own company
An `admin` SHALL be able to change another user's role between `admin` and `user` within their own company, subject to the same last-admin protection as removal.

#### Scenario: Admin promotes a teammate to admin
- **WHEN** an `admin` updates a `user`-role teammate in their own company to `role: admin`
- **THEN** the teammate's role is updated to `admin`

#### Scenario: Admin demotes another admin
- **WHEN** an `admin` demotes a different `admin`-role user in the same company to `role: user`, and at least one other admin remains after the change
- **THEN** the demotion succeeds

#### Scenario: Demoting the last admin is rejected
- **WHEN** an `admin` attempts to demote the only remaining `admin`-role user in their company (including themselves) to `role: user`
- **THEN** the system rejects the request and the role is unchanged

#### Scenario: Admin cannot grant superuser
- **WHEN** an `admin` submits a role update with `role: superuser`
- **THEN** the system rejects the request

### Requirement: Admin can update their own company's details
An `admin` SHALL be able to update their own company's `name`, `country`, `currency`, `is_ngo`, and `is_donor`.

#### Scenario: Admin updates company name
- **WHEN** an `admin` submits an update to their own company's `name`
- **THEN** the company record is updated and the change is reflected for all users of that company

#### Scenario: Admin changes their company's donor/grantee classification
- **WHEN** an `admin` submits an update setting `is_donor` and/or `is_ngo` on their own company
- **THEN** the company record is updated with the new classification

#### Scenario: Admin cannot update another company
- **WHEN** an `admin` submits an update targeting a `customer_id` other than their own
- **THEN** the system rejects the request as unauthorized
