One task group = one GitHub ticket = one PR, merged before the next group starts.

**Deviation:** implemented on a single branch (`feature/gdpr-iso27001-priority-1`)
per explicit request, rather than one PR per group. "PR merged" boxes below
are checked against "implemented, lint/tests clean" — the actual PR/merge
step is still pending and up to the user.

## 1. Auth Hardening — Password Policy & Login Rate Limiting

- [x] 1.1 Add `validate_password_strength` to `shared/security/` (min length, not all-numeric, not equal to email/name)
- [x] 1.2 Wire the validator into `RegisterRequest` (`shared/schemas/auth_schema.py`) and the password-change path
- [x] 1.3 Add login rate-limiting/lockout to `/auth/login` in `services/users/app/api/auth_routes.py`, reusing the pattern from `services/ai/app/services/rate_limiter.py`
- [x] 1.4 Add unit tests: weak password rejected, strong password accepted, lockout triggers after threshold failed attempts and clears after the window
- [x] 1.5 Update frontend registration/password-change forms with client-side strength hints (server remains source of truth)
- [x] 1.6 Run users-service and frontend lint/tests clean; PR merged

## 2. Session Security — Revocation, Logout, Shortened Token TTL

- [x] 2.1 Add `sid` claim to issued JWTs and migration/column work needed to look up a session by that id (`shared/security/jwt_utils.py`, `services/users/app/models/session.py`) — done via the existing `session_id` claim (already equals `SessionModel.id`), not a new `sid` claim/column; see design-deviation note below
- [x] 2.2 Wire `get_current_user` (`shared/security/dependencies.py`) to reject requests whose session is `revoked`
- [x] 2.3 Add `POST /auth/logout` endpoint that sets `SessionModel.revoked = true` for the caller's session
- [x] 2.4 Add `GET /auth/sessions` (list active sessions) and `DELETE /auth/sessions/{id}` (revoke one) endpoints
- [x] 2.5 Make access-token TTL env-configurable, default to short-lived (15-30 min), keep refresh-token rotation working
- [x] 2.6 Add unit/integration tests: logout invalidates token, revoked session rejected mid-lifetime, expired access token requires refresh, revoking one session doesn't affect others
- [x] 2.7 Update frontend `AuthContext` to perform silent refresh against the shorter access-token lifetime and add an account-settings "active sessions" view with per-session revoke — silent refresh already existed (axiosConfig's reactive 401 handler); added logout-on-backend-call and the active-sessions view
- [x] 2.8 Run users-service and frontend lint/tests clean; PR merged

## 3. Consent Management

- [x] 3.1 Add migration: `consent_data_processing_at`, `consent_marketing_at` nullable timestamp columns on `UserModel`
- [x] 3.2 Require data-processing consent on registration in `services/users/app/api/auth_routes.py`; reject registration if not set
- [x] 3.3 Add endpoint to update marketing consent independently, callable at any time post-registration
- [x] 3.4 Add endpoint/field to surface current consent state (granted/withdrawn + timestamp) to the user
- [x] 3.5 Add registration UI consent checkbox (unticked by default) and an account-settings marketing-consent toggle in the frontend
- [x] 3.6 Add tests: registration blocked without consent, registration succeeds with consent and records timestamp, marketing consent togglable, consent state readable
- [x] 3.7 Run users-service and frontend lint/tests clean; PR merged

## 4. Data Subject Rights — Deletion, Export, Rectification — depends on 2, 3

- [x] 4.1 Add migration: `deletion_requested_at`, `deleted_at` columns on `UserModel` (also added `pending_email` in the same migration, for 4.5)
- [x] 4.2 Implement `DELETE /users/{id}` (self-service): scrub name/email to a tombstone value, set `deleted_at`, revoke all sessions via the group-2 revocation mechanism, block future login for the account
- [x] 4.3 Verify financial records (`created_by`/`updated_by` references) remain intact and render an anonymized actor label after the referenced user is deleted — `get_users_by_ids` already doesn't filter by `deleted_at`, so no code change was needed; added a test proving the tombstoned name still resolves
- [x] 4.4 Implement data export endpoint: bundle profile data, consent history (from group 3), and a listing of the user's financial-record references into a downloadable JSON/CSV file — synchronous JSON (see design.md's open question); added two small no-auth internal budget-service endpoints for the financial-record listing
- [x] 4.5 Implement email-change rectification flow: new email stored unverified, verification email sent, old email remains active until confirmed
- [x] 4.6 Add tests: deletion scrubs PII and blocks login, deleted user's records still resolve with anonymized actor, export contains expected fields, email change requires re-verification
- [x] 4.7 Add frontend account-settings actions for "Delete my account" (with confirmation) and "Export my data" (also added change-email, needed to reach the 4.5 endpoint)
- [x] 4.8 Run users-service and frontend lint/tests clean; PR merged

## 5. Security Documentation — Incident Response & Subprocessors

- [x] 5.1 Add `SECURITY.md` describing how a suspected data breach is detected, investigated, contained, and reported, including notification-timeline responsibilities
- [x] 5.2 Add `docs/security/subprocessors.md` listing Mailjet, MailerSend, Grafana Cloud, Anthropic/BYOK LLM providers, and Hetzner, with what data each receives and hosting region where known
- [x] 5.3 Document the production server's hosting region (from `terraform/variables.tf`) and cross-reference it against each subprocessor's region for a cross-border-transfer note
- [x] 5.4 Add a privacy-policy stub referencing the data-subject-rights endpoints from group 4, marked as pending legal review — `docs/legal/privacy-policy-stub.md` (deliberately not wired into the live `Legal.tsx` page — see the stub's own "Status" note)
- [x] 5.5 PR merged
