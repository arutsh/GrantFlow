Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Data model + forgot-password request

- [x] 1.1 Add `password_reset_token_hash: str | None` and `password_reset_expires_at: datetime | None` columns to `UserModel` (`services/users/app/models/user.py`), mirroring the existing `email_verification_token_hash`/`email_verification_expires_at` pair.
- [x] 1.2 Generate the Alembic migration for the two new nullable columns (no backfill needed).
- [x] 1.3 Add `PASSWORD_RESET_TOKEN_TTL_HOURS = 1` constant and `set_password_reset_token`/`get_user_by_password_reset_token`-style CRUD helpers to `services/users/app/crud/user_crud.py`, mirroring `set_email_verification_token`, hashing via the existing `hash_token`/`verify_token_hash` (`shared/security/jwt_utils.py`). No-op (don't issue a token) when the target user has no `hashed_password` set.
- [x] 1.4 Add `POST /auth/forgot-password` to `auth_routes.py`: anonymous, enumeration-safe generic response, rate-limited via `login_rate_limiter.py` with `bucket="forgot_password"`, reuses `settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS` to optionally return `debug_token`.
- [x] 1.5 Add `send_password_reset_email` Celery task (`services/worker/tasks/users/send_password_reset_email.py`), mirroring `send_verification_email.py` — same retry/backoff config, built via `get_email_client()`.
- [x] 1.6 Add `enqueue_password_reset_email` to `services/users/app/services/celery_client.py`, call it from the new route.
- [ ] 1.7 Add `MAILERSEND_PASSWORD_RESET_TEMPLATE_ID` / `MAILJET_PASSWORD_RESET_TEMPLATE_ID` settings (`services/worker/config.py`) and create the corresponding template on both provider dashboards (dev + prod accounts); document the new env vars in `docs/deployment/DEPLOYMENT_MODES.md` alongside the existing MailerSend/Mailjet table.
  - [x] Settings + docs + env-file placeholders done.
  - [ ] Dashboard templates (dev + prod, both providers) — needs your provider-account access, not doable from here.
- [x] 1.8 Tests: token issuance/expiry/no-op-on-no-password in `user_crud`, route-level enumeration-safety + rate-limit tests for `forgot-password` (mirroring existing `resend-verification` tests in `test_auth_routes.py`), Celery task test mirroring `test_send_verification_email.py`.
- [ ] 1.9 Run the users-service and worker-service test/lint suites clean; PR merged.
  - [x] Tests/lint clean.
  - [ ] PR merged — awaiting commit/push approval.

## 2. Reset-password confirmation + session revocation — depends on 1

- [ ] 2.1 Add `POST /auth/reset-password` to `auth_routes.py`: validates token via the CRUD helper from 1.3, validates new password via `validate_password_strength`, sets `hashed_password`, clears the reset token/expiry, returns no session.
- [ ] 2.2 On successful reset, revoke every session for the account using `revoke_all_sessions_for_user` + `_revoke_session_everywhere` (dual-store: DB `revoked` flag + Redis), matching `change-password`'s revocation call but with no session preserved.
- [ ] 2.3 Add request/response schemas (`ForgotPasswordRequest/Response`, `ResetPasswordRequest/Response`) to `services/users/app/schemas/auth_schema.py`, following the existing `ResendVerificationRequest/Response` naming.
- [ ] 2.4 Tests: valid/expired/already-used/weak-password scenarios for `reset-password`, session-revocation assertions (all sessions gone, no new session issued), a test confirming a pending email-verification token is untouched by a password-reset request (and vice versa).
- [ ] 2.5 Run the users-service test/lint suite clean; PR merged.

## 3. Frontend request + confirm pages — depends on 1, 2

- [ ] 3.1 Add `ForgotPassword.tsx` page: email input, calls `POST /auth/forgot-password`, shows the same generic "check your email" confirmation regardless of outcome (no enumeration signal in the UI either).
- [ ] 3.2 Add `ResetPassword.tsx` page: reads the token from the URL query (mirroring `VerifyEmail.tsx`'s handling of its own token param), new-password + confirm-password inputs, calls `POST /auth/reset-password`, handles expired/already-used/weak-password error states distinctly, redirects to `/login` on success with a success message.
- [ ] 3.3 Wire both routes into `App.tsx` (`/forgot-password`, `/reset-password`) and add a "Forgot password?" link on `Login.tsx` next to the password field.
- [ ] 3.4 Manual verification: run the app, exercise the full flow end to end (request → email/debug token → confirm → old sessions dead → fresh login works), including the expired-token and wrong-password-strength error paths.
- [ ] 3.5 Run the frontend lint/typecheck/test suite clean; PR merged.
