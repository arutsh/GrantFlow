## ADDED Requirements

### Requirement: Direct superuser admin-console actions are logged even without an impersonation token
Each `superuser-admin-console` endpoint (customer list, user list, platform-AI-fallback toggle, user role update) SHALL write a `privileged_access_logs` entry when called, in the same shape as impersonation-triggered entries (actor, target `customer_id` and/or `user_id`, request path and method, timestamp), even though these requests carry no impersonation token.

#### Scenario: A list request from the admin console is logged
- **WHEN** a superuser requests the customer list or user list from the admin console
- **THEN** the system writes a `privileged_access_logs` entry recording the actor, the request, and the timestamp

#### Scenario: A toggle or role-update request from the admin console is logged
- **WHEN** a superuser toggles a customer's platform-AI-fallback default or updates a user's role via the admin console
- **THEN** the system writes a `privileged_access_logs` entry recording the actor, the target `customer_id`/`user_id`, the request, and the timestamp
