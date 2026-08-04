## ADDED Requirements

### Requirement: Donor creates a donor-grantee relationship
The system SHALL allow a customer with `is_donor = true` to create a `donor_grantees` record linking themselves, as donor, to a target customer with `is_ngo = true`, as grantee. The donor identity SHALL be derived from the authenticated caller's `customer_id` claim, never accepted from the request body, and the target grantee SHALL be identified by `grantee_id` in the request body. A caller with the `superuser` role is exempt from this derivation: since a superuser is not necessarily attached to any donor customer, they SHALL instead supply `donor_id` explicitly in the request body, and the request SHALL be rejected if they omit it.

#### Scenario: Donor successfully approves a grantee
- **WHEN** an authenticated user belonging to a donor customer (`is_donor = true`) submits `grantee_id` for a customer with `is_ngo = true`
- **THEN** the system creates a `donor_grantees` record with `donor_id` set to the caller's own `customer_id` and `grantee_id` set to the submitted value

#### Scenario: Non-donor cannot create a relationship
- **WHEN** an authenticated user whose customer has `is_donor = false` attempts to create a `donor_grantees` record
- **THEN** the system rejects the request and no record is created

#### Scenario: Target customer must be a grantee
- **WHEN** a donor submits a `grantee_id` for a customer with `is_ngo = false`
- **THEN** the system rejects the request and no record is created

#### Scenario: Caller cannot set donor_id explicitly
- **WHEN** a donor's create request includes a `donor_id` field pointing at a different donor customer
- **THEN** the system ignores the submitted value and uses the caller's own `customer_id` as `donor_id`

#### Scenario: Superuser creates a relationship on behalf of a donor
- **WHEN** an authenticated user with the `superuser` role submits `donor_id` and `grantee_id`
- **THEN** the system creates a `donor_grantees` record using the submitted `donor_id`, subject to the same donor/grantee role validation as a regular donor's request

#### Scenario: Superuser omitting donor_id is rejected
- **WHEN** an authenticated user with the `superuser` role submits a create request without `donor_id`
- **THEN** the system rejects the request and no record is created

### Requirement: A donor-grantee pair is unique
The system SHALL prevent more than one `donor_grantees` record existing for the same `(donor_id, grantee_id)` pair.

#### Scenario: Duplicate approval is rejected
- **WHEN** a donor attempts to create a `donor_grantees` record for a `(donor_id, grantee_id)` pair that already exists
- **THEN** the system rejects the request and no duplicate record is created

### Requirement: Donor lists and revokes their own relationships
The system SHALL allow a donor to list all `donor_grantees` records where they are the donor, and to delete a record where they are the donor. The system SHALL reject deletion of a record whose `donor_id` does not match the caller. A caller with the `superuser` role is exempt from this scoping: they SHALL be able to list any customer's relationships (given an explicit `customer_id`, rejected if omitted) and delete any record regardless of its `donor_id`.

#### Scenario: Donor lists their approved grantees
- **WHEN** a donor customer requests their own donor-side relationship list
- **THEN** the system returns all `donor_grantees` records where `donor_id` matches the caller's `customer_id`

#### Scenario: Donor revokes an approval
- **WHEN** a donor deletes a `donor_grantees` record where `donor_id` matches their own `customer_id`
- **THEN** the system removes the record

#### Scenario: Donor cannot revoke another donor's approval
- **WHEN** a donor attempts to delete a `donor_grantees` record whose `donor_id` does not match their own `customer_id`
- **THEN** the system rejects the request and the record is not removed

#### Scenario: Superuser lists any customer's relationships
- **WHEN** an authenticated user with the `superuser` role requests a relationship list with an explicit `customer_id` and `role`
- **THEN** the system returns the matching `donor_grantees` records for that `customer_id`, regardless of who the superuser is

#### Scenario: Superuser deletes any relationship
- **WHEN** an authenticated user with the `superuser` role deletes a `donor_grantees` record by `id`
- **THEN** the system removes the record regardless of its `donor_id`

### Requirement: Grantee has read-only visibility of their approving donors
The system SHALL allow a grantee to list the `donor_grantees` records where they are the grantee, and SHALL NOT allow a grantee to create or delete any `donor_grantees` record.

#### Scenario: Grantee lists their approving donors
- **WHEN** a grantee customer requests their own grantee-side relationship list
- **THEN** the system returns all `donor_grantees` records where `grantee_id` matches the caller's `customer_id`

#### Scenario: Grantee cannot create a relationship on their own behalf
- **WHEN** a user belonging to a grantee customer (`is_donor = false`) attempts to create a `donor_grantees` record
- **THEN** the system rejects the request and no record is created

### Requirement: Internal relationship-existence check
The system SHALL expose an internal endpoint that reports whether a `donor_grantees` record exists for a given `(donor_id, grantee_id)` pair, for use by other services, without requiring end-user authentication (matching the codebase's existing internal-service-endpoint convention).

#### Scenario: Relationship exists
- **WHEN** the internal existence check is called with a `(donor_id, grantee_id)` pair that has an approved record
- **THEN** the system reports that the relationship exists

#### Scenario: Relationship does not exist
- **WHEN** the internal existence check is called with a `(donor_id, grantee_id)` pair that has no record
- **THEN** the system reports that the relationship does not exist

### Requirement: Budget creation requires an approved donor-grantee relationship
The system SHALL reject creating a budget with `funding_customer_id` set unless a `donor_grantees` record exists linking that donor to the budget's resolved `owner_id`.

#### Scenario: Budget creation succeeds with an approved relationship
- **WHEN** a grantee creates a budget with `funding_customer_id` set to a donor that has approved them
- **THEN** the system creates the budget with `funding_customer_id` set

#### Scenario: Budget creation fails without an approved relationship
- **WHEN** a grantee creates a budget with `funding_customer_id` set to a donor that has not approved them
- **THEN** the system rejects the request and no budget is created

#### Scenario: Budget creation without a funder is unaffected
- **WHEN** a budget is created without `funding_customer_id` set (e.g. using `external_funder_name` instead)
- **THEN** the system does not perform the relationship check and creates the budget normally

### Requirement: Budget update requires an approved donor-grantee relationship
The system SHALL apply the same relationship check to any update that sets or changes a budget's `funding_customer_id`, using the budget's existing `owner_id`, so the create-time check cannot be bypassed via a subsequent edit.

#### Scenario: Attaching a funder to an existing budget succeeds with an approved relationship
- **WHEN** a grantee updates a funder-less budget to set `funding_customer_id` to a donor that has approved them
- **THEN** the system applies the update

#### Scenario: Attaching a funder to an existing budget fails without an approved relationship
- **WHEN** a grantee updates a funder-less budget to set `funding_customer_id` to a donor that has not approved them
- **THEN** the system rejects the update and the budget's `funding_customer_id` remains unchanged

### Requirement: Revocation does not retroactively affect existing budgets
The system SHALL NOT re-validate the donor-grantee relationship on already-created budgets when the relationship is later revoked; the check applies only at the moment `funding_customer_id` is set or changed.

#### Scenario: Existing funded budget survives revocation
- **WHEN** a donor revokes their approval of a grantee after a budget already exists with that donor as `funding_customer_id`
- **THEN** the existing budget's `funding_customer_id` remains set and the budget is otherwise unaffected

#### Scenario: New funding attempt fails after revocation
- **WHEN** a donor revokes their approval of a grantee and the grantee subsequently attempts to create or update a budget with that donor as `funding_customer_id`
- **THEN** the system rejects the request
