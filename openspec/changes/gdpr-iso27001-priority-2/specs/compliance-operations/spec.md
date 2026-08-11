## ADDED Requirements

### Requirement: Production Database Backups
The system SHALL run automated, encrypted backups of the production database on a scheduled basis, and the backups SHALL be stored separately from the production database host.

#### Scenario: Scheduled backup runs
- **WHEN** the scheduled backup job executes
- **THEN** an encrypted database backup artifact is produced and stored in a location distinct from the production database host

#### Scenario: Backup restore is verified
- **WHEN** a restore drill is performed using the most recent backup artifact
- **THEN** the restored database is verified to contain the expected data, confirming the backup is usable for recovery

### Requirement: Internal Service-to-Service Encryption in Transit
The system SHALL encrypt traffic between the gateway and backend services, not only between the gateway and external clients.

#### Scenario: Internal request between gateway and a backend service
- **WHEN** the gateway forwards a request to a backend service within the deployment network
- **THEN** that traffic is transmitted over an encrypted connection

### Requirement: Dependency Vulnerability Scanning
The system's CI pipeline SHALL automatically check backend and frontend dependencies for known vulnerabilities and surface findings for review.

#### Scenario: New dependency vulnerability disclosed
- **WHEN** a known vulnerability is disclosed for a dependency used by the project
- **THEN** an automated check surfaces the vulnerable dependency for review, without requiring a developer to check manually
