## MODIFIED Requirements

### Requirement: Founder becomes admin of a newly created company
When a non-superuser completes onboarding by supplying `new_customer_name` on `PATCH /users/{user_id}/` while their account status is `pending`, the system SHALL create the new company (customer), attach the user to it, activate the account, and SHALL set the user's role to `admin` as part of the same update. The newly created company SHALL have `is_ngo` set to `true`.

#### Scenario: Onboarding with a new company name promotes the founder to admin
- **WHEN** a pending, non-superuser account submits `PATCH /users/{user_id}/` with `new_customer_name` set to a company name
- **THEN** a new company is created, the user's `customer_id` is set to it, `status` becomes `active`, and `role` becomes `admin`

#### Scenario: Refreshed token reflects the promotion
- **WHEN** the founder's client calls `/auth/refresh` after the onboarding update succeeds
- **THEN** the newly issued access token carries `role: admin`, since token refresh reads the user's current role from the database rather than reusing the prior token's claim

#### Scenario: Self-registered company defaults to NGO
- **WHEN** a pending, non-superuser account submits `PATCH /users/{user_id}/` with `new_customer_name` set to a company name
- **THEN** the newly created company has `is_ngo = true`, making it immediately discoverable in donor grantee search and eligible to receive grants, with no manual Settings change required
