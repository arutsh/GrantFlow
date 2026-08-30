## Why

There is no self-service password recovery in GrantFlow: the only password-related endpoint is `POST /auth/change-password`, which requires an active session and the current password. A user who forgets their password has no path back into their account short of a manual DB fix — a real gap for a production nonprofit platform with real donor/grantee users, and one that surfaced while auditing auth flows (no ticket or OpenSpec change previously tracked it).

## What Changes

- Add an anonymous, email-based "forgot password" request endpoint that issues a single-use, expiring, hashed reset token and enqueues a reset email — enumeration-safe (same generic response whether or not the account exists) and rate-limited per email+IP, mirroring the existing `resend-verification` pattern.
- Add a reset-confirmation endpoint that accepts the token + new password, validates password strength, sets the new password hash, and invalidates the token.
- On successful reset, revoke **all** of the account's active sessions (there is no "current session" to preserve, unlike `change-password`) so a compromised session can't survive a legitimate password reset.
- Add a new hashed-token column pair on `UserModel` dedicated to password reset (not reusing `email_verification_token_hash`/`email_verification_expires_at`, since those are already reused by the pending-email-change flow and a reset request must not collide with or invalidate an in-flight email verification).
- Add a new Celery task + email template (mirrors `send_verification_email`) sent through the existing provider-agnostic `transactional-email` interface — no new provider work needed.
- Frontend: "Forgot password?" link on Login, a request-reset page, and a set-new-password page (token from the emailed link), plus a success/error state for expired or already-used tokens.

## Capabilities

### New Capabilities
- `password-reset`: anonymous request-token and confirm-reset endpoints, token lifecycle (issue/expire/single-use), reset email delivery, and the frontend request/confirm pages.

### Modified Capabilities
- `session-security`: adds a requirement that a successful password reset revokes every active session for the account (no session is preserved, since the flow starts unauthenticated) — same dual-store revocation (`revoked` flag + Redis) already used by `change-password`/logout.

## Impact

- **services/users**: new routes in `auth_routes.py` (`POST /auth/forgot-password`, `POST /auth/reset-password`), new CRUD helpers in `user_crud.py` (mirroring `set_email_verification_token`/`mark_email_verified`), new `UserModel` columns + Alembic migration, reuses `login_rate_limiter.py` with a new `bucket`.
- **services/worker**: new `send_password_reset_email` task + `MAILERSEND_/MAILJET_PASSWORD_RESET_TEMPLATE_ID` settings, new dashboard template on both providers.
- **frontend-typescript**: new pages (`ForgotPassword.tsx`, `ResetPassword.tsx`), new routes, a link from `Login.tsx`.
- **No gateway/nginx changes** — new routes fall under the existing `/api/v1/users/...` prefix already proxied to `services/users`.
