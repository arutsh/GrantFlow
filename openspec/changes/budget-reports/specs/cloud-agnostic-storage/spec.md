## ADDED Requirements

### Requirement: S3-compatible storage interface
The system SHALL provide a storage abstraction with `save`, `open_stream`/read, `delete`, and `exists` operations backed by an S3-compatible object store, not hardcoding any single provider.

#### Scenario: Save and retrieve a file through the abstraction
- **WHEN** a caller saves a file's bytes through the storage abstraction under a given key
- **THEN** the same key can later be used to retrieve the identical bytes

#### Scenario: Delete a file through the abstraction
- **WHEN** a caller deletes a file by its key through the storage abstraction
- **THEN** subsequent attempts to read that key fail, and the abstraction reports the key no longer exists

### Requirement: Backend selection via configuration only
The system SHALL allow pointing the storage abstraction at any S3-compatible endpoint (e.g. a self-hosted MinIO instance for local development, or a hosted provider such as Cloudflare R2 for production) purely through configuration, without requiring changes to the calling business logic.

#### Scenario: Switching endpoint does not change caller code
- **WHEN** the configured storage endpoint, credentials, or bucket are changed to point at a different S3-compatible provider
- **THEN** callers of the storage abstraction continue to use the same `save`/`open_stream`/`delete`/`exists` interface unchanged

### Requirement: Local development uses a self-hosted S3-compatible backend
The system SHALL run a local S3-compatible object store (MinIO) as part of local development, so the storage abstraction exercises real object-storage semantics rather than a local-filesystem stand-in that could behave differently from production.

#### Scenario: Local dev targets the local MinIO container
- **WHEN** the budget service starts locally with the default development configuration
- **THEN** file operations through the storage abstraction go against the local MinIO container, using the same code path production uses against its own S3-compatible provider
