## ADDED Requirements

### Requirement: Consent Capture at Registration
The system SHALL require an affirmative, unticked-by-default consent to data processing before a new account can be created, and SHALL record the timestamp at which consent was given.

#### Scenario: Registration without required consent
- **WHEN** a registration request is submitted without the data-processing consent flag set
- **THEN** the system rejects the registration with a validation error

#### Scenario: Registration with required consent
- **WHEN** a registration request is submitted with the data-processing consent flag set
- **THEN** the system creates the account and records the consent timestamp

### Requirement: Optional Marketing Consent
The system SHALL allow a user to separately opt in or out of marketing communications, independent of the mandatory data-processing consent, and SHALL allow this preference to be changed at any time after registration.

#### Scenario: User withdraws marketing consent
- **WHEN** an authenticated user disables marketing consent in account settings
- **THEN** the system clears the marketing consent timestamp and the user receives no further marketing email

### Requirement: Consent State Auditable
The system SHALL make a user's current consent state (data processing, marketing) visible to that user and to administrators handling a data-subject request.

#### Scenario: User views their consent state
- **WHEN** an authenticated user views their account settings
- **THEN** the system displays whether data-processing and marketing consent are currently active, and when each was last granted or withdrawn
