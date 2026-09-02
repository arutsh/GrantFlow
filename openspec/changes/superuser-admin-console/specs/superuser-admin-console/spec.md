## ADDED Requirements

### Requirement: Superuser-only admin console is reachable at `/admin`
The frontend SHALL provide a route at `/admin` that renders the admin console. The console, and any nav entry linking to it, SHALL be visible and reachable only to users whose token carries `role: superuser`.

#### Scenario: Superuser sees and opens the admin console
- **WHEN** a user with `role: superuser` is authenticated
- **THEN** a nav entry (or direct navigation to `/admin`) is available and renders the console

#### Scenario: Non-superuser cannot reach the admin console
- **WHEN** a user without `role: superuser` navigates to `/admin`, directly or via URL
- **THEN** the system does not render the console content and no nav entry links to it

### Requirement: Superuser can list all customers
The system SHALL provide a superuser-only endpoint that returns every customer, independent of any impersonation session, including at minimum: name, country, `is_ngo`, `is_donor`, currency, deactivated status, and whether platform-AI-fallback is enabled as that customer's default.

#### Scenario: Superuser lists all customers
- **WHEN** a superuser with no active impersonation session requests the customer list from the admin console
- **THEN** the system returns every customer in the platform, not scoped to any single tenant

#### Scenario: Non-superuser cannot list all customers
- **WHEN** a caller without `role: superuser` requests this endpoint
- **THEN** the system rejects the request

### Requirement: Superuser can toggle a customer's platform-AI-fallback default from the console
The system SHALL provide a superuser-only endpoint that enables or disables platform-AI-fallback as a customer's default, addressed by explicit `customer_id`, without requiring an active impersonation session for that customer.

#### Scenario: Superuser enables platform-fallback for a customer directly
- **WHEN** a superuser, without impersonating that customer, toggles platform-AI-fallback on for a given `customer_id` from the admin console
- **THEN** that customer's AI default resolves to the platform-funded model, matching the effect of the existing impersonation-scoped toggle

#### Scenario: Superuser disables platform-fallback for a customer directly
- **WHEN** a superuser, without impersonating that customer, toggles platform-AI-fallback off for a given `customer_id`
- **THEN** that customer's platform-fallback default is cleared

#### Scenario: Non-superuser cannot use the direct toggle
- **WHEN** a caller without `role: superuser` calls this endpoint
- **THEN** the system rejects the request

### Requirement: Superuser can list all users
The system SHALL provide a superuser-only endpoint that returns every user across every customer, including at minimum: name, email, `customer_id`/customer name, role, and status.

#### Scenario: Superuser lists all users
- **WHEN** a superuser with no active impersonation session requests the user list from the admin console
- **THEN** the system returns users belonging to every customer, not scoped to any single tenant

#### Scenario: Non-superuser cannot list all users
- **WHEN** a caller without `role: superuser` requests this endpoint
- **THEN** the system rejects the request

### Requirement: Superuser can update a user's role/admin status from the console
The system SHALL provide a superuser-only endpoint that updates a user's role, addressed by explicit `user_id`, without requiring an active impersonation session for that user's customer. This endpoint SHALL apply the same last-admin protection `company-user-administration` already enforces, so a superuser cannot leave a company with zero active admins via this path.

#### Scenario: Superuser promotes a user directly
- **WHEN** a superuser updates a user's role to `admin` by `user_id` from the admin console
- **THEN** the user's role is updated, matching the effect of the equivalent impersonation-based promotion

#### Scenario: Superuser cannot demote a company's last admin via the console
- **WHEN** a superuser attempts to demote or remove admin status from a user who is the sole active admin of their company
- **THEN** the system rejects the request, the same as it would for a company's own admin attempting the same action

#### Scenario: Non-superuser cannot use the direct role-update endpoint
- **WHEN** a caller without `role: superuser` calls this endpoint
- **THEN** the system rejects the request
