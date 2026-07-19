## ADDED Requirements

### Requirement: Backend-agnostic storage interface
The system SHALL provide a storage abstraction with `save`, `open_stream`/read, `delete`, and `exists` operations that do not hardcode any specific cloud provider, selecting the concrete backend from configuration at runtime.

#### Scenario: Save and retrieve a file through the abstraction
- **WHEN** a caller saves a file's bytes through the storage abstraction under a given key
- **THEN** the same key can later be used to retrieve the identical bytes, regardless of which backend is configured

#### Scenario: Delete a file through the abstraction
- **WHEN** a caller deletes a file by its key through the storage abstraction
- **THEN** subsequent attempts to read that key fail, and the abstraction reports the key no longer exists

### Requirement: Local filesystem as the default backend
The system SHALL default to a local filesystem backend rooted at a configurable path, requiring no external service to be provisioned, so the feature works out of the box on the project's current (non-cloud-object-storage) infrastructure.

#### Scenario: Default configuration uses local disk
- **WHEN** no alternative storage backend is configured
- **THEN** files are saved under and read from the configured local directory

### Requirement: Backend selection via configuration only
The system SHALL allow switching the storage backend (e.g. to an S3-compatible, Azure Blob, or GCS backend) by changing configuration alone, without requiring changes to the calling business logic.

#### Scenario: Switching backend does not change caller code
- **WHEN** the configured storage backend URI is changed to point at a different backend type
- **THEN** callers of the storage abstraction continue to use the same `save`/`open_stream`/`delete`/`exists` interface unchanged
