## ADDED Requirements

### Requirement: Multiple attachments per report line
The system SHALL allow a report line to have zero or more file attachments, each recording the original filename, content type, size, and a reference to where the file's bytes are stored.

#### Scenario: Upload a receipt to a report line
- **WHEN** a user with access uploads a file to a report line on a draft report
- **THEN** the system stores the file's bytes via the storage abstraction and creates an `Attachment` record linked to that report line

#### Scenario: Upload multiple attachments to one report line
- **WHEN** a user uploads a second file (e.g. a payment proof) to a report line that already has an attachment
- **THEN** both attachments exist independently under that report line

### Requirement: Upload validation
The system SHALL reject file uploads exceeding 15MB or whose content type is not in the allowed set (PDF, JPEG, PNG, HEIC).

#### Scenario: Oversized file rejected
- **WHEN** a user attempts to upload a file larger than 15MB
- **THEN** the system rejects the upload without storing it

#### Scenario: Disallowed content type rejected
- **WHEN** a user attempts to upload a file whose content type is not PDF, JPEG, PNG, or HEIC
- **THEN** the system rejects the upload without storing it

### Requirement: Attachments lock outside of draft status
The system SHALL prevent uploading or deleting attachments on a report line whose parent report is not in `draft` status.

#### Scenario: Cannot upload to a submitted report's line
- **WHEN** a user attempts to upload an attachment to a report line whose parent report is not in `draft` status
- **THEN** the system rejects the upload

### Requirement: Authenticated attachment retrieval
The system SHALL allow downloading an attachment's file content only to users with access to the underlying budget (owner or funder), re-checking that access on every download, and SHALL NOT expose attachments via a public or unauthenticated URL.

#### Scenario: Authorized user downloads an attachment
- **WHEN** a user with access to the budget requests an attachment's content
- **THEN** the system streams the file's bytes back with its recorded content type

#### Scenario: Unauthorized user cannot download an attachment
- **WHEN** a user without access to the budget requests an attachment's content
- **THEN** the system rejects the request with a permission error

### Requirement: Attachment deletion
The system SHALL allow deleting an attachment (removing both its stored bytes and its record) while its parent report is in `draft` status.

#### Scenario: Delete an attachment from a draft report
- **WHEN** a user with access deletes an attachment on a report line belonging to a draft report
- **THEN** the attachment's stored file and its record are both removed
