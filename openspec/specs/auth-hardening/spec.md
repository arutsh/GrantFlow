# auth-hardening Specification

## Purpose
TBD - created by archiving change gdpr-iso27001-priority-1. Update Purpose after archive.
## Requirements
### Requirement: Password Complexity Policy
The system SHALL enforce a minimum password strength (minimum length, not entirely numeric, not identical to the account's email or name) on registration and on any password change.

#### Scenario: Registration with weak password
- **WHEN** a registration request is submitted with a password that does not meet the minimum strength policy
- **THEN** the system rejects the registration with a validation error explaining the policy

### Requirement: Login Rate Limiting
The system SHALL limit the rate of failed login attempts per account and per source IP, and SHALL temporarily lock out further attempts once a threshold is exceeded.

#### Scenario: Repeated failed login attempts
- **WHEN** an account receives more failed login attempts than the configured threshold within the configured window
- **THEN** the system rejects further login attempts for that account until the lockout window elapses, even if correct credentials are supplied

