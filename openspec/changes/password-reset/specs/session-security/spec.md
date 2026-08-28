## ADDED Requirements

### Requirement: Password Reset Revokes All Sessions
The system SHALL revoke every active session belonging to an account when a password reset is successfully confirmed, since the reset request originates from an unauthenticated context with no current session to preserve, unlike an authenticated password change. Revocation SHALL use the same dual-store mechanism (persisted `revoked` flag plus the cross-service Redis check) already used for logout and authenticated password change.

#### Scenario: Successful reset revokes every session
- **WHEN** a password-reset confirmation succeeds
- **THEN** every session for that account is marked revoked in both the database and the cross-service Redis check, so no previously issued access or refresh token for that account remains valid

#### Scenario: Reset does not issue a replacement session
- **WHEN** a password-reset confirmation succeeds and prior sessions are revoked
- **THEN** the response contains no access token, refresh token, or session identifier — the user must log in again with the new password
