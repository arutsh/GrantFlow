## ADDED Requirements

### Requirement: Superuser can set a customer's platform-fallback default directly, without impersonation
Alongside the existing impersonation-scoped route (which resolves the target `customer_id` from the caller's token), the system SHALL provide a superuser-only route that enables or disables platform-AI-fallback as a customer's default given an explicit `customer_id`, callable without an active impersonation session for that customer. Both routes SHALL write through the same underlying platform-fallback state, so a customer's resolved default never depends on which route last set it.

#### Scenario: Direct toggle and impersonation-scoped toggle agree
- **WHEN** a superuser enables platform-fallback for a customer via the direct by-id route, and later an admin of that same customer (or an impersonating superuser) views AI settings
- **THEN** the customer's default is shown as platform-fallback, identically to if it had been set via the impersonation-scoped route

#### Scenario: Non-superuser cannot use the direct route
- **WHEN** a caller without `role: superuser` calls the direct by-id platform-fallback route
- **THEN** the system rejects the request with a 403
