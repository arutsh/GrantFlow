## ADDED Requirements

### Requirement: Transactional emails link to the Privacy Policy
The system SHALL include a link to the Privacy Policy in every
transactional email it sends, regardless of which provider is active.

#### Scenario: Verification email includes a privacy link
- **WHEN** the system enqueues a verification email
- **THEN** the personalization data passed to the provider includes a
  `privacy_url` pointing at the live Privacy Policy page

#### Scenario: Invite email includes a privacy link
- **WHEN** the system enqueues an admin-invite email
- **THEN** the personalization data passed to the provider includes a
  `privacy_url` pointing at the live Privacy Policy page

#### Scenario: Privacy link works regardless of active provider
- **WHEN** `EMAIL_PROVIDER` is `mailjet` or `mailersend`
- **THEN** the corresponding dashboard-hosted template for that provider
  renders the `privacy_url` variable as a visible link in the sent email
