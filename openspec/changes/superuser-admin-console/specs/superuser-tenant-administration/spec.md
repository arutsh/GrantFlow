## MODIFIED Requirements

### Requirement: Superuser manages any company's users via impersonation
A `superuser` SHALL be able to invite, remove, and promote/demote users, and update company details, for any company by first starting an impersonation session for that company's `customer_id` (per the `customer-impersonation` capability) and then using the same `company-user-administration` endpoints an admin of that company would use. The sole exception is updating a user's role/admin status, for which the `superuser-admin-console` capability also provides a direct endpoint addressed by explicit `user_id` (no impersonation session required); invite, remove, and company-detail updates remain impersonation-only with no dedicated superuser-scoped endpoints.

#### Scenario: Superuser removes a user in another company
- **WHEN** a superuser has an active impersonation session for a target `customer_id` and requests removal of a user belonging to that `customer_id`
- **THEN** the request succeeds via the same authorization path `company-user-administration` uses for an admin, because the impersonation token carries `role: admin` scoped to that `customer_id`

#### Scenario: Superuser without an active session for that company cannot act on it
- **WHEN** a superuser has no active impersonation session, or one impersonating a different `customer_id`, and requests removal of a user or an update to a company outside that scope
- **THEN** the request is rejected, per the `customer-impersonation` capability's scoping rules

#### Scenario: Superuser promotes/demotes a user directly via the admin console, without impersonation
- **WHEN** a superuser with no active impersonation session updates a user's role via the `superuser-admin-console` role-update endpoint
- **THEN** the request succeeds, as the one named exception to this requirement's impersonation-only rule
