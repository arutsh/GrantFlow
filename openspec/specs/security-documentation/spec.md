# security-documentation Specification

## Purpose
TBD - created by archiving change gdpr-iso27001-priority-1. Update Purpose after archive.
## Requirements
### Requirement: Documented Incident Response Process
The project SHALL maintain a written incident response process describing how a suspected data breach is detected, investigated, and reported, sufficient to support timely breach notification obligations.

#### Scenario: Suspected breach identified
- **WHEN** a team member suspects a data breach has occurred
- **THEN** a documented process exists describing the steps to investigate, contain, and determine notification obligations

### Requirement: Documented Subprocessors
The project SHALL maintain a written list of third-party subprocessors that process personal data on the platform's behalf, including what data each subprocessor receives and, where known, where that data is hosted.

#### Scenario: New subprocessor introduced
- **WHEN** a new third-party service is integrated that receives personal data (e.g., an email provider or LLM API)
- **THEN** it is added to the documented subprocessor list before or at the time it goes live in production

