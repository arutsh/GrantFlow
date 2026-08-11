# data-subject-rights Specification

## Purpose
TBD - created by archiving change gdpr-iso27001-priority-1. Update Purpose after archive.
## Requirements
### Requirement: Account Deletion (Right to Erasure)
The system SHALL allow an authenticated user to request deletion of their account. On deletion, the system SHALL scrub personal identifiers (name, email) from the user's record, revoke all active sessions for that user, and prevent future login, while retaining anonymized references on financial records the user created for institutional record-keeping purposes.

#### Scenario: User requests account deletion
- **WHEN** an authenticated user submits a delete-account request
- **THEN** the system marks the account deleted, replaces the name and email with an anonymized tombstone value, and revokes all of the user's active sessions

#### Scenario: Deleted user attempts to log in
- **WHEN** a request is made to authenticate with credentials belonging to a deleted account
- **THEN** the system rejects the login attempt

#### Scenario: Deleted user's financial records remain attributable
- **WHEN** a budget or report created by a now-deleted user is viewed by another authorized user
- **THEN** the record remains present and shows an anonymized actor reference instead of a broken or missing link

### Requirement: Personal Data Export (Right to Access)
The system SHALL allow an authenticated user to request an export of the personal data associated with their account, delivered in a structured, machine-readable format (JSON or CSV).

#### Scenario: User requests data export
- **WHEN** an authenticated user submits a data export request
- **THEN** the system generates a file containing the user's profile data, consent history, and a listing of financial records they created, and makes it available for download

### Requirement: Data Rectification
The system SHALL allow an authenticated user to correct inaccurate personal data (name, email) beyond the fields already editable via the existing profile update endpoint, and SHALL require re-verification when the email address is changed.

#### Scenario: User updates email address
- **WHEN** an authenticated user submits a new email address
- **THEN** the system stores the new address as unverified and sends a new verification email before it is treated as confirmed

