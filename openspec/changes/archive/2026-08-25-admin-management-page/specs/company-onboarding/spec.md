## MODIFIED Requirements

### Requirement: Founder's admin role is immediately usable elsewhere
Once a founder holds `role: admin`, every existing capability already gated on `admin`/`superuser` SHALL treat them as authorized, with no per-capability change required — the role promotion is the only thing that needed to happen.

#### Scenario: Founder can manage org-level AI settings right after onboarding
- **WHEN** a founder who just created their company refreshes their access token and calls an endpoint under `/ai/settings` (gated on `role in {"admin", "superuser"}` in `services/ai/app/api/settings_routes.py`)
- **THEN** the request succeeds on the strength of the `admin` role claim alone, with no change needed in the AI service

#### Scenario: Inviting other teammates is now covered by a dedicated capability
- **WHEN** a company admin wants to add a teammate to their company
- **THEN** the admin uses the invitation mechanism defined by the `company-user-administration` capability, rather than requiring a superuser to assign the teammate's `customer_id`/`role` directly
