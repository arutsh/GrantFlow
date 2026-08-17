# ai-provider-settings Specification

## Purpose
TBD - created by archiving change superuser-cross-tenant-access. Update Purpose after archive.
## Requirements
### Requirement: AI provider settings are scoped by customer, not by individual user
The system SHALL store and look up AI provider key/model configuration (`UserProviderKey`) by the acting user's `customer_id`, not by their individual `user_id`. Any admin-or-above user acting for a customer — including a superuser impersonating that customer — SHALL see and modify the same configuration as any other admin-or-above user of that customer.

#### Scenario: One admin sees another admin's configured key
- **WHEN** an admin of a customer configures an AI provider key, and a different admin of the same customer subsequently views AI settings
- **THEN** the second admin sees the key as configured, not as unconfigured

#### Scenario: Impersonating superuser and the customer's own admin see the same configuration
- **WHEN** a superuser impersonating a customer configures an AI provider key, and the customer's own admin subsequently views AI settings
- **THEN** the admin sees the key as configured, matching what the superuser set

