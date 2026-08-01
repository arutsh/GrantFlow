## ADDED Requirements

### Requirement: Attachment list per report line
The frontend SHALL list a report line's attachments (filename, size, content type) sourced from `GET /attachments/by-report-line/{report_line_id}`.

#### Scenario: Attachments shown under a report line
- **WHEN** a report line has one or more attachments
- **THEN** the report detail view lists each attachment's filename under that line

### Requirement: Attachment upload while draft
The frontend SHALL let the report owner upload a file to a report line via multipart `POST /attachments/` while the parent report's status is `draft`, and SHALL hide or disable the upload control once the report leaves `draft`.

#### Scenario: Upload succeeds
- **WHEN** the owner selects a file for a report line on a `draft` report and confirms upload
- **THEN** the frontend sends a multipart `POST /attachments/` with `report_line_id` and the file, and appends the resulting attachment to that line's list on success

#### Scenario: Upload control hidden outside draft
- **WHEN** the parent report's status is `submitted`, `approved`, or `rejected`
- **THEN** the report detail view does not show an upload control for that report's lines

### Requirement: Client-side upload validation
The frontend SHALL reject, before sending the request, a file larger than 15MB or whose type is not one of PDF, JPEG, PNG, or HEIC, showing an inline error naming the violated constraint.

#### Scenario: Oversized file rejected client-side
- **WHEN** the user selects a file larger than 15MB
- **THEN** the frontend shows an error and does not send `POST /attachments/`

#### Scenario: Disallowed content type rejected client-side
- **WHEN** the user selects a file whose type is not PDF, JPEG, PNG, or HEIC
- **THEN** the frontend shows an error and does not send `POST /attachments/`

#### Scenario: Backend rejects despite client-side pass
- **WHEN** a file passes client-side validation but the backend still rejects the upload
- **THEN** the frontend shows the backend's error message without leaving a partial attachment in the displayed list

### Requirement: Attachment download
The frontend SHALL let a user with view access to the report download an attachment's content via `GET /attachments/{id}/content`.

#### Scenario: Download an attachment
- **WHEN** the user clicks an attachment's filename or a download control
- **THEN** the frontend requests `GET /attachments/{id}/content` and triggers a browser download using the attachment's original filename

### Requirement: Attachment deletion while draft
The frontend SHALL let the report owner delete an attachment via `DELETE /attachments/{id}/` while the parent report's status is `draft`, and SHALL hide the delete control once the report leaves `draft`.

#### Scenario: Delete an attachment
- **WHEN** the owner clicks "Delete" on an attachment belonging to a `draft` report's line
- **THEN** the frontend calls `DELETE /attachments/{id}/` and removes it from the displayed list on success

#### Scenario: Delete control hidden outside draft
- **WHEN** the parent report's status is not `draft`
- **THEN** the report detail view does not show a delete control for that report's attachments
