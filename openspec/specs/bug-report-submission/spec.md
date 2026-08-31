# bug-report-submission Specification

## Purpose
TBD - created by archiving change user-bug-report. Update Purpose after archive.
## Requirements
### Requirement: Submit a bug report
An authenticated user SHALL be able to submit a bug report consisting of free-text description and auto-captured context (current page path, browser/user agent, client timestamp). The system SHALL persist the report regardless of whether the downstream notification succeeds.

#### Scenario: Successful submission
- **WHEN** an authenticated user submits a report with a non-empty description and context fields
- **THEN** the system creates a `bug_reports` record with the submitter's user id, description, and context, and returns success to the client

#### Scenario: Notification failure does not fail submission
- **WHEN** a report is submitted and the downstream notification dispatch fails or is delayed
- **THEN** the report is still persisted and the submission request still returns success

#### Scenario: Unauthenticated request rejected
- **WHEN** a request to submit a report is made without a valid session
- **THEN** the system rejects it with an authentication error and does not create a record

### Requirement: Optional screenshot attachment
A submitted report MAY include a single screenshot image. The system SHALL validate the file's actual content type (not just the declared header) and size before accepting it, and SHALL store it in object storage rather than inline in the database.

#### Scenario: Valid screenshot accepted
- **WHEN** a report is submitted with an image file of an allowed type (PNG, JPEG, or WebP) at or under the size limit
- **THEN** the system uploads it to object storage and stores a reference to it on the report record

#### Scenario: Oversized screenshot rejected
- **WHEN** a report is submitted with an image file exceeding the configured size limit
- **THEN** the system rejects the request with a validation error and does not create the report or upload the file

#### Scenario: Disallowed or spoofed file type rejected
- **WHEN** a report is submitted with a file whose actual content (sniffed from its bytes) is not one of the allowed image types, regardless of the declared content type
- **THEN** the system rejects the request with a validation error

#### Scenario: Report without a screenshot
- **WHEN** a report is submitted with no file attached
- **THEN** the system creates the report record with no screenshot reference, and no upload is attempted

### Requirement: Asynchronous notification dispatch
Submitting a report SHALL enqueue a notification dispatch job rather than sending the notification synchronously within the request.

#### Scenario: Submission returns before notification completes
- **WHEN** a report is successfully persisted
- **THEN** the system enqueues a background job to dispatch a notification and returns the submission response without waiting for that job to complete

