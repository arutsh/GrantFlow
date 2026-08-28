## ADDED Requirements

### Requirement: Transactional emails link to the Privacy Policy
The system SHALL pass a `privacy_url` personalization value pointing at the
live Privacy Policy page in every transactional email send, regardless of
which provider is active. Whether that value renders as a visible link
depends on the active provider's dashboard-hosted template having been
updated to include it — a per-provider, manual, outside-this-repo step.

#### Scenario: Verification email includes a privacy link
- **WHEN** the system enqueues a verification email
- **THEN** the personalization data passed to the provider includes a
  `privacy_url` pointing at the live Privacy Policy page

#### Scenario: Invite email includes a privacy link
- **WHEN** the system enqueues an admin-invite email
- **THEN** the personalization data passed to the provider includes a
  `privacy_url` pointing at the live Privacy Policy page

#### Scenario: Privacy link renders for the active provider (Mailjet)
- **WHEN** `EMAIL_PROVIDER` is `mailjet`
- **THEN** the Mailjet dashboard-hosted template renders the `privacy_url`
  variable as a visible link in the sent email

#### Scenario: MailerSend template not yet updated
- **WHEN** `EMAIL_PROVIDER` is `mailersend`
- **THEN** `privacy_url` is still sent in the personalization data, but the
  MailerSend dashboard template has not been edited to render it — the
  template must be updated before MailerSend is made the active provider
  again
