## MODIFIED Requirements

### Requirement: Superuser has no cross-tenant data access outside an active impersonation session
A caller with the `superuser` role but no active impersonation session (no `customer_id` resolved on their token) SHALL NOT receive another customer's data through any endpoint, with a narrow, explicit exception for the `superuser-admin-console` endpoints (customer list, user list, platform-AI-fallback toggle by `customer_id`, user role update by `user_id`), which are independently superuser-gated and take their target id explicitly rather than resolving it from the token. Outside that named exception, list endpoints SHALL return an empty result and single-resource endpoints SHALL behave as not-found, rather than falling back to returning data across all customers. Impersonation SHALL remain the only channel for every other cross-tenant action; no endpoint other than the named `superuser-admin-console` set SHALL grant a blanket bypass based on the `superuser` role alone.

#### Scenario: Superuser without an active session lists a resource
- **WHEN** a superuser with no active impersonation session requests a list of budgets, reports, or other customer-owned resources
- **THEN** the system returns an empty result, not the resources of every customer

#### Scenario: Superuser without an active session requests a specific resource
- **WHEN** a superuser with no active impersonation session requests a specific customer's resource by id
- **THEN** the system responds as if the resource does not exist

#### Scenario: Superuser with an active session sees exactly the impersonated customer's data
- **WHEN** a superuser has an active impersonation session for a target customer
- **THEN** the system scopes their requests to that customer exactly as it would for that customer's own user, with no special-casing based on the `superuser` role

#### Scenario: Superuser uses the admin console without an active impersonation session
- **WHEN** a superuser with no active impersonation session calls a `superuser-admin-console` endpoint (customer list, user list, platform-AI-fallback toggle, or user role update)
- **THEN** the request succeeds and is scoped to the explicit `customer_id`/`user_id` the request names, as the named exception to this requirement

#### Scenario: A non-admin-console endpoint still refuses the superuser-role-alone bypass
- **WHEN** a superuser with no active impersonation session calls any endpoint other than the named `superuser-admin-console` set
- **THEN** the system applies the empty-result / not-found behavior above, exactly as before this change
