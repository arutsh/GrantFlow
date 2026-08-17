# privileged-access-audit Specification

## Purpose
TBD - created by archiving change superuser-cross-tenant-access. Update Purpose after archive.
## Requirements
### Requirement: Every request under an impersonation session is logged
Each service SHALL maintain its own append-only `privileged_access_logs` table, local to that service's database. Whenever a request is made using an impersonation token (per the `customer-impersonation` capability), the system SHALL log it — at minimum the acting superuser's identity, the target `customer_id`, the request path and method, and a timestamp — regardless of whether the request is a read or a write.

#### Scenario: A view performed during impersonation is logged
- **WHEN** a superuser, while impersonating a customer, makes a read-only request
- **THEN** the system writes a `privileged_access_logs` entry recording the actor, target customer, request, and timestamp

#### Scenario: A write performed during impersonation is logged
- **WHEN** a superuser, while impersonating a customer, makes a request that changes data
- **THEN** the system writes a `privileged_access_logs` entry recording the actor, target customer, request, and timestamp

#### Scenario: Requests outside an impersonation session are not logged as privileged
- **WHEN** a customer's own user makes a request using their normal (non-impersonation) session
- **THEN** the system does not write a `privileged_access_logs` entry

### Requirement: Privileged access log entries are immutable
The system SHALL NOT provide any way to update or delete a `privileged_access_logs` entry through the application.

#### Scenario: No update path exists
- **WHEN** any code path attempts to modify an existing `privileged_access_logs` entry
- **THEN** no such application code path exists; entries are write-once

