## MODIFIED Requirements

### Requirement: Active Session Visibility
The system SHALL allow an authenticated user to view their active sessions and revoke any one of them individually. A session is considered "active" for this purpose only if it is both not revoked and not past its expiration time; expired sessions SHALL NOT appear in the listed sessions regardless of their revoked status.

#### Scenario: User revokes a specific session
- **WHEN** an authenticated user requests revocation of one of their listed active sessions
- **THEN** the system revokes that session without affecting the user's other active sessions

#### Scenario: Expired session excluded from listing
- **WHEN** an authenticated user requests their active sessions and one of their sessions has an `expires_at` in the past but was never explicitly revoked
- **THEN** that session is excluded from the returned list

## ADDED Requirements

### Requirement: Expired Session Purge
The system SHALL periodically delete session records whose expiration time has passed, so that expired sessions do not accumulate indefinitely in storage.

#### Scenario: Scheduled purge removes expired sessions
- **WHEN** the scheduled session-cleanup task runs
- **THEN** all session records with `expires_at` in the past are deleted from the database

#### Scenario: Non-expired sessions are untouched by purge
- **WHEN** the scheduled session-cleanup task runs
- **THEN** session records that are not yet expired, whether revoked or not, remain in the database
