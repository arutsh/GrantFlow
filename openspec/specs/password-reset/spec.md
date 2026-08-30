# password-reset Specification

## Purpose
TBD - created by archiving change password-reset. Update Purpose after archive.
## Requirements
### Requirement: Forgot-password request endpoint
The system SHALL provide an unauthenticated endpoint, identified by email address, that issues a new single-use, expiring password-reset token and enqueues a reset email for an account with a set password, invalidating any previously issued reset token for that account. The endpoint SHALL be rate-limited per combined email+source-IP key, and SHALL return an identical, generic response regardless of whether the account exists, has a password set, or the request succeeded, to prevent account enumeration.

#### Scenario: Request for an account with a password
- **WHEN** the owner of an account that has a password set requests a password reset, without needing to be logged in
- **THEN** a new hashed token and expiry are generated, any prior reset token is invalidated, and a reset email is enqueued

#### Scenario: Request for a nonexistent email
- **WHEN** a reset is requested for an email with no matching account
- **THEN** the system SHALL NOT reveal that the account does not exist, and SHALL return the same generic response as a successful request

#### Scenario: Request for an account with no password set
- **WHEN** a reset is requested for an account that has never had a password set (e.g. an invited user who has not yet accepted)
- **THEN** the system SHALL NOT generate a reset token or enqueue an email, but SHALL return the same generic response as a successful request

#### Scenario: Rate limit exceeded
- **WHEN** the combined email+IP request count for the `forgot_password` bucket exceeds the configured maximum within the lockout window
- **THEN** the system rejects further requests with a 429 response until the window expires

### Requirement: Reset-password confirmation endpoint
The system SHALL provide an endpoint that accepts a password-reset token and a new password, validates the token is unexpired and matches a stored token hash for an account, validates the new password against the platform's password-strength policy, and on success sets the account's password hash and clears the stored token so it cannot be reused. The endpoint SHALL NOT issue an access token, refresh token, or session.

#### Scenario: Valid token resets the password
- **WHEN** a user submits a reset token that matches a stored, unexpired token for their account, with a new password meeting the strength policy
- **THEN** the account's password hash is updated, the stored reset token and expiry are cleared, and the response confirms success without issuing any session

#### Scenario: Expired token is rejected
- **WHEN** a user submits a reset token whose expiry timestamp has passed
- **THEN** the request is rejected and the account's password is unchanged

#### Scenario: Already-used token is rejected
- **WHEN** a user submits a reset token that was already consumed by a prior successful reset
- **THEN** the request is rejected because no matching pending token exists

#### Scenario: Weak new password is rejected
- **WHEN** a user submits a valid, unexpired reset token but a new password that fails the platform's password-strength policy
- **THEN** the request is rejected, the stored reset token is left intact, and the account's password is unchanged

### Requirement: Password-reset token is single-purpose and short-lived
The system SHALL store the password-reset token as a hashed value on a dedicated column pair, separate from the email-verification token, so that a password-reset request cannot invalidate an in-flight email-verification or pending-email-change token and vice versa. The token SHALL expire 1 hour after issuance.

#### Scenario: Reset request does not disturb a pending email verification
- **WHEN** an account has a pending, unexpired email-verification token and its owner requests a password reset
- **THEN** the email-verification token remains valid and unaffected, and a separate password-reset token is issued

#### Scenario: Token expires after one hour
- **WHEN** a reset-password confirmation is submitted more than one hour after the token was issued
- **THEN** the system treats the token as expired and rejects the request

