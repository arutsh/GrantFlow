# transactional-email Specification

## Purpose
Provider-agnostic capability for sending transactional emails (starting with the verification email use case), with the active provider selected at runtime via `EMAIL_PROVIDER`, and MailerSend + Mailjet as the initial pluggable implementations.

## Requirements
### Requirement: Provider-agnostic transactional email interface
The system SHALL expose a single interface for sending a transactional email (recipient, subject, template identifier, personalization data) that every supported email provider implements identically, so callers depend only on that interface and not on any vendor-specific request or response shape.

#### Scenario: Call site is provider-neutral
- **WHEN** a Celery task sends a transactional email
- **THEN** it calls the shared interface only, with no MailerSend- or Mailjet-specific types, payload shapes, or fields present at the call site

### Requirement: Runtime provider selection via configuration
The system SHALL select which email provider implementation is active based on an `EMAIL_PROVIDER` configuration value, without requiring a code change to switch providers.

#### Scenario: Default provider is MailerSend
- **WHEN** `EMAIL_PROVIDER` is unset
- **THEN** the system uses the MailerSend implementation, preserving existing behavior

#### Scenario: Mailjet selected via configuration
- **WHEN** `EMAIL_PROVIDER` is set to `mailjet`
- **THEN** the system uses the Mailjet implementation for all transactional email sends

#### Scenario: Unsupported provider value fails fast
- **WHEN** `EMAIL_PROVIDER` is set to a value that matches no supported provider
- **THEN** the worker raises a clear configuration error at startup rather than silently falling back to a default provider

### Requirement: MailerSend and Mailjet both fully supported
The system SHALL provide working, independently configurable implementations for both MailerSend and Mailjet, each capable of sending the verification email end-to-end when selected as the active provider.

#### Scenario: MailerSend remains functional
- **WHEN** `EMAIL_PROVIDER` is `mailersend` (or unset) and a verification email is enqueued
- **THEN** the email is sent via MailerSend's API using existing `MAILERSEND_*` configuration, unchanged from prior behavior

#### Scenario: Mailjet is functional
- **WHEN** `EMAIL_PROVIDER` is `mailjet` and a verification email is enqueued
- **THEN** the email is sent via Mailjet's API using `MAILJET_*` configuration

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

### Requirement: Common error type across providers
The system SHALL raise a shared, provider-independent error type when a transactional email send fails, regardless of which provider is active, so error-handling logic does not need to special-case each vendor.

#### Scenario: Send failure raises the shared error type
- **WHEN** either provider's API call fails with a network error or an HTTP error response
- **THEN** the system raises the shared email-provider error type, not a provider-specific exception unknown to the caller
