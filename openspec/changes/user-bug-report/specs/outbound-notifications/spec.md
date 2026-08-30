## ADDED Requirements

### Requirement: Provider-agnostic notification interface
The system SHALL define a channel-neutral notification message and dispatch it through a swappable provider interface. Callers SHALL depend only on this interface, never on a specific channel's API or payload shape.

#### Scenario: Caller is decoupled from the concrete channel
- **WHEN** code elsewhere in the system needs to notify the team of an event
- **THEN** it constructs a channel-neutral message (title, body, contextual fields, optional link) and passes it to the configured provider, without referencing Slack or any other specific channel

#### Scenario: Swapping providers requires no caller changes
- **WHEN** the configured provider is changed from one implementation to another (e.g. Slack to email)
- **THEN** no code that constructs or sends notification messages needs to change, only the provider configuration

### Requirement: Slack Incoming Webhook provider
The system SHALL provide a Slack implementation of the notification interface that posts a formatted message to a configured Slack Incoming Webhook URL. It SHALL work against a free Slack plan, which does not support inline file uploads via webhook.

#### Scenario: Message delivered to Slack
- **WHEN** a notification is dispatched through the Slack provider with a configured webhook URL
- **THEN** the provider posts a message to that webhook containing the title, body, and contextual fields

#### Scenario: Linked attachment instead of inline upload
- **WHEN** a notification includes a link to an attachment (e.g. a screenshot)
- **THEN** the Slack message includes that link as clickable text rather than attempting to upload the file inline

#### Scenario: Transient delivery failure is retried
- **WHEN** the Slack webhook call fails with a retryable error (network error, 5xx, or 429 response)
- **THEN** the dispatch is retried with backoff rather than being dropped permanently

#### Scenario: Non-retryable failure is not retried
- **WHEN** the Slack webhook call fails with a non-retryable error (e.g. 400 invalid payload, 404 unknown webhook)
- **THEN** the dispatch fails without further retries

### Requirement: No-op fallback when unconfigured
When no webhook URL (or other provider-specific destination) is configured, the system SHALL fall back to a no-op provider that logs the notification instead of failing, so local development and tests do not require a live external destination.

#### Scenario: Missing configuration does not raise an error
- **WHEN** a notification is dispatched and no destination is configured for the active provider
- **THEN** the system logs the notification content and returns without raising an error
