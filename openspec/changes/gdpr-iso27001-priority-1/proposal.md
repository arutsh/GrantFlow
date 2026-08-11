## Why

A codebase audit found GrandFlow has no GDPR data-subject rights, no consent capture, no session/token revocation, and no password/lockout policy — the gaps that are both the most legally load-bearing (GDPR Art. 15/17, lawful basis for processing) and the most externally checkable (a donor's technical diligence, or a user simply testing "can I delete my account"). This is priority 1 of a two-part compliance program: these items must land before the team can credibly say, anywhere public, that the platform is "built with GDPR compliance in mind." Priority 2 (retention jobs, backups, internal TLS, dependency scanning) is tracked separately as it's operational hardening that isn't blocking that public claim.

## What Changes

- Add logout and session/token revocation (activate the currently-dead `SessionModel.revoked` field); shorten access-token lifetime.
- Enforce password complexity on registration and password-change, and add login rate-limiting/lockout. (No grandfathering needed — there are no production users yet.)
- Add consent capture at registration/onboarding, stored and auditable.
- Add account/data deletion, data export, and rectification endpoints (data subject rights).
- Add `SECURITY.md` (incident-response process) and a subprocessor/DPA document (Mailjet, MailerSend, Grafana Cloud, Anthropic/BYOK, Hetzner) so the compliance claim has something concrete to link to.

## Capabilities

### New Capabilities
- `session-security`: logout, refresh/access token revocation, active-session listing, shorter token lifetimes.
- `auth-hardening`: password complexity policy and login rate-limiting/lockout.
- `consent-management`: capture, store, and let users withdraw consent for data processing and marketing email.
- `data-subject-rights`: user-initiated account deletion, personal-data export, and rectification beyond partial `PATCH`.
- `security-documentation`: written incident-response process and a documented subprocessor list.

### Modified Capabilities
(none — all changes are additive; no existing spec's requirements are being altered)

## Impact

- **services/users**: `auth_routes.py` (logout, rate limiting, password validation), `user_routes.py` (delete/export/rectify), `models/session.py` (activate `revoked`), `models/user.py` (consent field).
- **shared/security**: `jwt_utils.py` (token lifetime, revocation check), `dependencies.py`.
- **shared/schemas**: `auth_schema.py` password validation.
- **frontend-typescript**: registration consent UI, account settings (delete/export/logout/sessions), move tokens out of `localStorage` where feasible, silent-refresh support for shorter token TTL.
- **New docs**: `SECURITY.md`, `docs/security/subprocessors.md`, privacy-policy stub.
- **New DB migrations**: consent field, deletion field, session id claim support.
