# session-security Specification

## Purpose
TBD - created by archiving change gdpr-iso27001-priority-1. Update Purpose after archive.
## Requirements
### Requirement: Explicit Logout
The system SHALL provide a logout endpoint that revokes the caller's current session, after which the session's tokens SHALL no longer be accepted for authentication.

#### Scenario: User logs out
- **WHEN** an authenticated user calls the logout endpoint
- **THEN** the system marks the associated session as revoked

#### Scenario: Revoked session reused
- **WHEN** a request presents an access token belonging to a revoked session
- **THEN** the system rejects the request as unauthenticated

### Requirement: Session Revocation Enforced on Every Request
The system SHALL check session revocation status as part of authenticating every request that carries a bearer token, not only at token issuance.

#### Scenario: Session revoked mid-lifetime
- **WHEN** a session is revoked while its access token has not yet expired
- **THEN** subsequent requests using that access token are rejected before its natural expiry

### Requirement: Bounded Access Token Lifetime
The system SHALL issue access tokens with a lifetime short enough to limit the exposure window of a stolen token, and SHALL support renewing access without re-authentication via the existing refresh-token flow.

#### Scenario: Expired access token
- **WHEN** a request presents an access token past its configured lifetime
- **THEN** the system rejects the request and the client must use its refresh token to obtain a new access token

### Requirement: Active Session Visibility
The system SHALL allow an authenticated user to view their active sessions and revoke any one of them individually.

#### Scenario: User revokes a specific session
- **WHEN** an authenticated user requests revocation of one of their listed active sessions
- **THEN** the system revokes that session without affecting the user's other active sessions

### Requirement: Session Authentication Requires Verified Email
The system SHALL reject an otherwise-valid, non-revoked, unexpired access token if its `email_verified` claim is not true, at the same shared dependency that authenticates every request across all services. The rejection SHALL use a distinct status/response from an invalid or expired token, so clients can distinguish "needs to verify" from "needs to re-authenticate."

#### Scenario: Unverified token rejected on a protected endpoint
- **WHEN** a request presents an access token whose `email_verified` claim is false, but is otherwise valid and not revoked
- **THEN** the system rejects the request with a 403 response indicating the account is not verified, distinct from the 401 used for invalid/expired/revoked tokens

#### Scenario: Verified token behaves as before
- **WHEN** a request presents an access token whose `email_verified` claim is true
- **THEN** authentication proceeds exactly as it did before this change

### Requirement: Pending Accounts' Sessions Revoked At Rollout
The system SHALL, as a one-time migration step at deployment of this change, revoke all existing sessions belonging to accounts whose `email_verified` is false, so server-side enforcement takes effect immediately rather than waiting for those sessions' tokens to expire naturally.

#### Scenario: Migration revokes pending users' sessions
- **WHEN** the rollout migration runs against the existing sessions table
- **THEN** every session belonging to a user with `email_verified = false` is marked revoked, and previously verified users' sessions are left untouched

