# company-onboarding Specification

## Purpose
TBD - created by archiving change new-company-user-admin. Update Purpose after archive.
## Requirements
### Requirement: Founder becomes admin of a newly created company
When a non-superuser completes onboarding by supplying `new_customer_name` on `PATCH /users/{user_id}/` while their account status is `pending`, the system SHALL create the new company (customer), attach the user to it, activate the account, and SHALL set the user's role to `admin` as part of the same update.

#### Scenario: Onboarding with a new company name promotes the founder to admin
- **WHEN** a pending, non-superuser account submits `PATCH /users/{user_id}/` with `new_customer_name` set to a company name
- **THEN** a new company is created, the user's `customer_id` is set to it, `status` becomes `active`, and `role` becomes `admin`

#### Scenario: Refreshed token reflects the promotion
- **WHEN** the founder's client calls `/auth/refresh` after the onboarding update succeeds
- **THEN** the newly issued access token carries `role: admin`, since token refresh reads the user's current role from the database rather than reusing the prior token's claim

### Requirement: Founder's admin role is immediately usable elsewhere
Once a founder holds `role: admin`, every existing capability already gated on `admin`/`superuser` SHALL treat them as authorized, with no per-capability change required — the role promotion is the only thing that needed to happen.

#### Scenario: Founder can manage org-level AI settings right after onboarding
- **WHEN** a founder who just created their company refreshes their access token and calls an endpoint under `/ai/settings` (gated on `role in {"admin", "superuser"}` in `services/ai/app/api/settings_routes.py`)
- **THEN** the request succeeds on the strength of the `admin` role claim alone, with no change needed in the AI service

#### Scenario: Inviting other teammates is not part of this capability
- **WHEN** a company admin wants to add a teammate to their company
- **THEN** no self-service invitation mechanism exists yet — only a superuser can assign another user's `customer_id`/`role` — and that gap is explicitly out of scope for this capability, tracked as separate follow-on work

### Requirement: Joining an existing company does not change role
When a user attaches to an already-existing company by supplying `customer_id` (rather than `new_customer_name`) during onboarding, the system SHALL leave their role unchanged.

#### Scenario: Joining an existing company keeps the default role
- **WHEN** a pending, non-superuser account submits `PATCH /users/{user_id}/` with `customer_id` pointing at an existing company (no `new_customer_name`)
- **THEN** the user's `customer_id` is set to that company and their `role` remains whatever it was before the request (the registration default, `user`)

### Requirement: Promotion is scoped to admin, not superuser
The role assigned to a company founder SHALL be exactly `admin`, and the system SHALL NOT grant `superuser` through this or any other self-service onboarding path.

#### Scenario: New-company onboarding never grants superuser
- **WHEN** any non-superuser account creates a new company via `new_customer_name` during onboarding
- **THEN** the resulting role is `admin`, never `superuser`, regardless of any role value the client may have sent in the request body

