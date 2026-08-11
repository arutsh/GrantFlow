## ADDED Requirements

### Requirement: AI Audit Prompt Retention Limit
The system SHALL automatically purge or redact the raw prompt text stored in AI audit log records after a configurable retention period, while preserving non-content metadata (timestamps, user reference, token counts) indefinitely for audit purposes.

#### Scenario: AI audit record past retention window
- **WHEN** a scheduled retention job runs and finds AI audit log records with raw prompt text older than the configured retention period
- **THEN** the job redacts or removes the prompt text while leaving the record's metadata fields intact

### Requirement: Chat Message Retention Limit
The system SHALL automatically purge chat conversation messages after a configurable period of conversation inactivity.

#### Scenario: Inactive conversation past retention window
- **WHEN** a scheduled retention job runs and finds a chat conversation with no activity for longer than the configured retention period
- **THEN** the job deletes the conversation's messages
