## ADDED Requirements

### Requirement: A customer cannot be its own donor-grantee relationship
The system SHALL reject creating a `donor_grantees` record where `donor_id` equals `grantee_id`. This closes a gap surfaced by `company-user-administration`'s "Admin can update their own company's details" requirement, which lets a company self-service-configure `is_ngo` and `is_donor` simultaneously — making a self-referential donor-grantee relationship reachable for the first time.

#### Scenario: Creating a donor-grantee relationship with the same customer on both sides is rejected
- **WHEN** a request to create a donor-grantee relationship supplies the same `customer_id` for both `donor_id` and `grantee_id`
- **THEN** the system rejects the request with a 400 error and no relationship is created
