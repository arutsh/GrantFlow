## ADDED Requirements

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
