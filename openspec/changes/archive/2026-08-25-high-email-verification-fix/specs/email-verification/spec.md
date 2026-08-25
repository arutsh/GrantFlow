## ADDED Requirements

### Requirement: Registration does not grant a session
The system SHALL NOT issue an access token, refresh token, or session as part of a successful `POST /register` response. Registration SHALL only create the pending account, generate a verification token, and enqueue the confirmation email.

#### Scenario: Registration returns a non-authenticating confirmation
- **WHEN** a new user completes `POST /register` with a valid, unique email
- **THEN** the response contains no access token, refresh token, or session identifier, and the account remains unauthenticated until email verification succeeds

## MODIFIED Requirements

### Requirement: Email verification endpoint
The system SHALL provide an endpoint that accepts a verification token, marks the corresponding account as verified when the token is valid and unexpired, and rejects invalid, expired, or already-used tokens. On successful verification, the system SHALL issue a new access token, refresh token, and session for the account, since this is the first point at which a session is authorized to exist.

#### Scenario: Valid token verifies the account
- **WHEN** a user submits a verification token that matches a stored, unexpired token for their account
- **THEN** the account's `email_verified` flag is set to true and the stored token is cleared so it cannot be reused

#### Scenario: Expired token is rejected
- **WHEN** a user submits a verification token whose expiry timestamp has passed
- **THEN** the request is rejected and the account remains unverified

#### Scenario: Already-used token is rejected
- **WHEN** a user submits a verification token that was already consumed by a prior successful verification
- **THEN** the request is rejected because no matching pending token exists

#### Scenario: Successful verification issues a session
- **WHEN** a verification token is successfully validated and the account is marked verified
- **THEN** the response includes a new access token and refresh token whose `email_verified` claim is true, and a corresponding session is created

### Requirement: Resend verification email
The system SHALL provide an unauthenticated endpoint, identified by email address, that issues a new verification token and enqueues a new confirmation email for an account that is not yet verified, invalidating any previously issued token for that account. The endpoint SHALL be rate-limited per combined email+source-IP key, and SHALL return an identical, generic response regardless of whether the account exists, is already verified, or is pending, to prevent account enumeration.

#### Scenario: Resend for an unverified account
- **WHEN** an unverified account's owner requests a resend of the verification email, without needing to be logged in
- **THEN** a new token and expiry are generated, any prior token is invalidated, and a new confirmation email is enqueued

#### Scenario: Resend for an already-verified account
- **WHEN** a resend is requested for an email belonging to an already-verified account
- **THEN** the system SHALL NOT generate a new token or enqueue an email, but SHALL return the same generic response as a successful resend

#### Scenario: Resend for a nonexistent email
- **WHEN** a resend is requested for an email with no matching account
- **THEN** the system SHALL NOT reveal that the account does not exist, and SHALL return the same generic response as a successful resend

### Requirement: Login remains available to unverified users
The system SHALL allow a user with an unverified email to submit correct credentials to `POST /login`, but SHALL NOT issue an access token, refresh token, or session in response. Instead the system SHALL return a distinct, non-authenticating response indicating the account requires verification, directing the user toward the resend-verification endpoint.

#### Scenario: Unverified user submits correct credentials
- **WHEN** a registered but unverified user submits correct credentials to `POST /login`
- **THEN** the system confirms the credentials were valid but issues no token or session, and the response indicates the account needs email verification

#### Scenario: Verified user logs in as before
- **WHEN** a registered and verified user submits correct credentials to `POST /login`
- **THEN** authentication succeeds exactly as before this change, with a session issued and `email_verified: true` in the JWT

### Requirement: Verification state reflected in JWT claims
The system SHALL include an `email_verified` boolean claim in every issued JWT, kept consistent with the account's current verification state at the time of issuance.

#### Scenario: Claim reflects current state at token issuance
- **WHEN** a JWT is issued at email verification, login, or refresh
- **THEN** the token's `email_verified` claim matches the account's `email_verified` value in the database at that moment

## REMOVED Requirements

### Requirement: Onboarding gated on email verification
**Reason**: Superseded by server-side enforcement at the shared session-authentication dependency (see `session-security` capability), which now rejects any request from an unverified account across every protected endpoint, not just onboarding. Since unverified accounts no longer hold a session at all, the narrower onboarding-only gate is subsumed by the broader one.

**Migration**: No client action needed. Any code that specifically checked this onboarding-only gate should rely on the general protected-access enforcement instead.

