## ADDED Requirements

### Requirement: An organization can save multiple configs per provider
The system SHALL allow a customer to save more than one `UserProviderKey` row for the same provider, each independently created and deleted, optionally carrying a `label` for display purposes.

#### Scenario: Second config for the same provider
- **WHEN** an admin saves a new Anthropic config for an organization that already has one Anthropic config configured
- **THEN** both configs are stored and both remain independently visible and usable, not overwritten

### Requirement: Exactly one saved config is the organization's default
Among a customer's saved configs, at most one SHALL be marked default at any time. When resolving which provider/model to use for a request that doesn't specify one, the system SHALL use the config marked default, not the most recently modified one.

#### Scenario: Setting a new default unsets the previous one
- **WHEN** an admin marks a non-default config as default
- **THEN** that config becomes the default and the previously-default config is no longer marked default

#### Scenario: Resolution uses the default, not recency
- **WHEN** a customer has multiple configured configs and a non-default one was modified most recently
- **THEN** requests that don't specify a model resolve to the config marked default, not the most recently modified one

### Requirement: Deleting the default config requires an explicit next step
The system SHALL reject a request to delete a customer's default config unless the request also specifies either another existing config of that customer to promote to default, or an explicit choice to fall back to the platform-funded model (see platform-fallback requirement below).

#### Scenario: Delete default without a replacement is rejected
- **WHEN** an admin requests deletion of the org's current default config without naming a replacement default or choosing the platform fallback
- **THEN** the system rejects the deletion with an error, and the config and its default status are unchanged

#### Scenario: Delete default with a named replacement succeeds
- **WHEN** an admin requests deletion of the org's current default config and names another of the org's existing configs as the new default
- **THEN** the named config becomes the new default and the deleted config is removed, in the same operation

#### Scenario: Deleting an organization's last remaining config is allowed
- **WHEN** an admin deletes a customer's only remaining config
- **THEN** the deletion succeeds and the customer is left with no configs and no default, without requiring a replacement or fallback choice

### Requirement: Only a superuser may set the platform-funded model as an organization's default
Choosing GrantFlow's platform-funded model as a customer's explicit default (rather than one of its own BYOK configs) SHALL require the acting user to have the `superuser` role. An `admin` acting for the customer SHALL NOT be able to enable this on their own.

#### Scenario: Admin attempts to enable platform-funded default
- **WHEN** a user with role `admin` requests that the platform-funded model be set as their organization's default
- **THEN** the system rejects the request with a 403

#### Scenario: Superuser enables platform-funded default
- **WHEN** a user with role `superuser` requests that the platform-funded model be set as an organization's default
- **THEN** the request succeeds and that organization's default resolves to the platform-funded model until changed

## MODIFIED Requirements

### Requirement: AI provider settings are scoped by customer, not by individual user
The system SHALL store and look up AI provider key/model configuration (`UserProviderKey`) by the acting user's `customer_id`, not by their individual `user_id`. Any admin-or-above user acting for a customer — including a superuser impersonating that customer — SHALL see and modify the same set of configs, and the same default, as any other admin-or-above user of that customer. A customer may have zero, one, or multiple configs; the customer-scoping applies to the whole set, not to a single provider-keyed row.

#### Scenario: One admin sees another admin's configured key
- **WHEN** an admin of a customer configures an AI provider key, and a different admin of the same customer subsequently views AI settings
- **THEN** the second admin sees the key as configured, not as unconfigured

#### Scenario: Impersonating superuser and the customer's own admin see the same configuration
- **WHEN** a superuser impersonating a customer configures an AI provider key, and the customer's own admin subsequently views AI settings
- **THEN** the admin sees the key as configured, matching what the superuser set

#### Scenario: Admins of the same customer share the same set of configs and default
- **WHEN** one admin of a customer adds a second config and marks it default
- **THEN** any other admin-or-above user of that same customer sees both configs and the same one marked default
