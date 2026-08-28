## Context

`services/users/app/api/auth_routes.py` already has a working, well-tested pattern for exactly this shape of problem: `resend-verification` is an anonymous, enumeration-safe, rate-limited endpoint that issues a hashed single-use expiring token and enqueues an email; `verify-email` consumes that token. Password reset is the same shape (request → hashed token → email → confirm), so this design reuses every piece of existing infrastructure rather than inventing new patterns:

- `hash_token`/`verify_token_hash` (`shared/security/jwt_utils.py`)
- `is_locked_out`/`record_failed_attempt`/`clear_failed_attempts` (`services/users/app/services/login_rate_limiter.py`), keyed by a new `bucket`
- `revoke_all_sessions_for_user` + the dual-store (`Postgres` + Redis) revocation helper `_revoke_session_everywhere` already used by `change-password`/logout
- The provider-agnostic `transactional-email` interface and the `tasks.users.send_verification_email` Celery task as the template for a new `send_password_reset_email` task
- `validate_password_strength` (`shared/security/password_policy.py`), already used by `change-password`

**Non-Goals:**
- Changing how `change-password` (authenticated, current-password-required) works — untouched, it stays the path for a logged-in user who knows their password.
- Building account lockout/abuse tooling beyond the existing rate-limit pattern.
- Any new email provider work — both MailerSend and Mailjet already implement the shared send interface; this only adds a new template ID + task.

## Goals / Non-Goals

**Goals:**
- An anonymous user who forgot their password can recover account access via email, without an admin or DB intervention.
- The new flow is enumeration-safe and rate-limited to the same standard as `resend-verification`.
- A successful reset can't leave a stolen/hijacked session alive.

**Non-Goals:** (see Context above)

## Decisions

**Dedicated token columns, not a reuse of `email_verification_token_hash`/`email_verification_expires_at`.**
Those columns are already dual-purposed (initial registration verification *and* the pending-email-change flow from `data-subject-rights`). Adding password reset as a third consumer would mean a reset request silently invalidates an in-flight email-change verification (and vice versa) — a confusing cross-feature side effect. Add `password_reset_token_hash: str | None` and `password_reset_expires_at: datetime | None` to `UserModel` instead, mirroring the existing pair exactly (same nullable `String`/`DateTime` types, same hash-on-write/clear-on-consume lifecycle). New Alembic migration, both nullable so no backfill needed.

**Token TTL: 1 hour, not the 24-hour email-verification TTL.**
A password-reset token grants an *account takeover* if intercepted (attacker sets a new password directly), which is higher-impact than an email-verification token (which only flips a boolean). Industry-standard reset TTLs are short (Auth0/Okta default 1 hour or less). Add `PASSWORD_RESET_TOKEN_TTL_HOURS = 1` as a module constant in `user_crud.py`, next to the existing `EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24`.

**Confirm-reset revokes *all* sessions, not "all but current" like `change-password`.**
`change-password` preserves the caller's own session because the caller is already authenticated in it. `reset-password` has no authenticated session at all — the request is anonymous by definition — so there is no session to preserve. Every existing session for the account is revoked via the same dual-store `_revoke_session_everywhere` helper, then the client is expected to log in fresh with the new password (mirrors `verify-email`'s "this is a login moment" precedent, but reset does *not* auto-issue a session — see next decision).

**Reset confirmation does not auto-issue a session.**
Unlike `verify-email` (which issues a session because it's the first-ever authenticated moment for that account), a password reset is not proof of "this is a device the account owner already trusts" — reusing the reset token as an implicit login would let anyone with a compromised inbox get a live session, not just a new password. The response is a plain success/failure; the user logs in normally afterward.

**Enumeration-safety and rate-limit bucket: exact copy of `resend-verification`.**
New `bucket="forgot_password"` key in the existing Redis-backed limiter (same `LOGIN_MAX_ATTEMPTS`/`LOGIN_LOCKOUT_SECONDS` settings, no new config). `POST /auth/forgot-password` always returns the same generic `{"sent": true}` shape regardless of whether the account exists, is unverified, or has no password set (e.g. an invited user who never accepted).

**`EXPOSE_VERIFICATION_TOKEN_FOR_TESTS`-style test escape hatch, reused.**
The existing `settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS` flag already exists purely so integration tests can read a raw token without parsing email content. Reuse the same flag (not a new one) to optionally return `debug_token` from `forgot-password` too — keeps the test-only surface area to one setting instead of two.

## Risks / Trade-offs

**[Risk] A reset token intercepted in transit (compromised inbox) is a full account takeover vector, more so than the verification token.** → Mitigated by the short 1-hour TTL, single-use enforcement (token cleared on consumption, same as email verification), and immediate all-session revocation on success so an attacker who resets first still gets logged out the moment the real owner resets again.

**[Risk] Two anonymous, similarly-shaped endpoints (`resend-verification`, `forgot-password`) both keyed on email+IP could be confused or share a rate-limit bucket by mistake during implementation.** → Mitigated by using a distinct `bucket` string (`"forgot_password"`) end to end, same as `change_password` already does for its own bucket; tests should assert the buckets don't cross-contaminate (a lockout on one doesn't block the other).

**[Risk] Silent failure if the reset email enqueue fails**, same class of bug that caused the Mailjet incident to go unnoticed for email verification (bare `except Exception: logger.exception(...)` swallows the error). → Not fixed here (out of scope, tracked separately as a hardening backlog item from that incident); `forgot-password` will follow the same swallow-and-log pattern as `resend-verification` for consistency, not because it's ideal.

## Migration Plan

1. Alembic migration adding `password_reset_token_hash`/`password_reset_expires_at` (nullable, no data migration).
2. Ship backend endpoints + worker task + email templates behind normal deploy (no feature flag needed — purely additive, no existing behavior changes).
3. Ship frontend pages/routes.
4. Rollback: revert the migration is safe (columns unused elsewhere) and the endpoints are additive — no rollback ordering constraint with other in-flight changes.

## Open Questions

- Should `forgot-password` be blocked (or allowed) for accounts with `hashed_password IS NULL` (invited-but-never-accepted users)? Current lean: allow it silently to succeed (generic response either way per enumeration-safety) but the CRUD layer should no-op rather than set a reset token for a null-password account, since "resetting" a password that doesn't exist yet is a set-invite-password case, not a reset case — deferred to tasks/implementation to confirm against `accept-invite`'s existing behavior.
