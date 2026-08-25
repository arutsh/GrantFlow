## ADDED Requirements

### Requirement: Resend-Verification Rate Limiting
The system SHALL limit the rate of resend-verification requests per combined email+source-IP key, using the same lockout mechanism applied to login and registration, matching the existing `auth-hardening` rate-limiting pattern.

#### Scenario: Repeated resend requests from one source
- **WHEN** a combined email+source-IP key submits more resend-verification requests than the configured threshold within the configured window
- **THEN** the system rejects further resend requests for that key with a 429 response until the lockout window elapses

## MODIFIED Requirements

### Requirement: Registration Cannot Set Privileged Role
The system SHALL ignore any `role` value supplied by the client on `POST /api/register` and SHALL always create the new account with role `user`. Elevation to `admin` or `superuser` SHALL only be possible through the `company-onboarding` promotion path or the protected admin-management endpoints, never through registration. Since registration no longer returns a session, this SHALL be verified against the persisted account record and, once available, the role claim of the session issued at successful email verification — not against a token returned by registration itself.

#### Scenario: Client attempts to self-register as superuser
- **WHEN** an unauthenticated caller submits `POST /api/register` with `"role": "superuser"` (or any value other than `user`) in the request body
- **THEN** the account is created with `role: user`, and the session subsequently issued at successful email verification carries a `role` claim of `user`

#### Scenario: Client attempts to self-register as admin
- **WHEN** an unauthenticated caller submits `POST /api/register` with `"role": "admin"` in the request body
- **THEN** the account is created with `role: user`, and the session subsequently issued at successful email verification carries a `role` claim of `user`
