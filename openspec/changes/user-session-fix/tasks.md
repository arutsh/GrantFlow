One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Filter expired sessions out of the active-sessions listing

- [ ] 1.1 Update `get_non_revoked_sessions_for_user` in `services/users/app/crud/sessions_curd.py` to also filter `SessionModel.expires_at > now(UTC)`, so expired-but-not-revoked sessions are excluded.
- [ ] 1.2 Add/update unit tests for `get_non_revoked_sessions_for_user` covering: non-revoked+non-expired (included), non-revoked+expired (excluded), revoked+non-expired (excluded).
- [ ] 1.3 Add/update an integration test for `GET /auth/sessions` (`services/users/app/api/auth_routes.py`) asserting an expired session does not appear in the response.
- [ ] 1.4 Manually verify in the running app: log in, confirm the settings "Active sessions" panel no longer lists sessions past their `expires_at`.
- [ ] 1.5 Run users-service tests and lint (flake8 --max-line-length=100) clean; PR merged (`Closes` the ticket).

## 2. Scheduled purge of expired session records — independent of group 1, may ship in either order

- [ ] 2.1 Add `USERS_DATABASE_URL` to `services/worker/config.py`, mirroring the existing `AI_DATABASE_URL` pattern.
- [ ] 2.2 Create `services/worker/tasks/users/cleanup_sessions.py` following the structure of `services/worker/tasks/ai/cleanup_sessions.py`: lazy-initialized engine against `USERS_DATABASE_URL`, `DELETE FROM user_sessions WHERE expires_at < :cutoff RETURNING id`, task name `tasks.users.cleanup_sessions`.
- [ ] 2.3 Register the new task module in `celery_app.py`'s `include` list and add a `beat_schedule` entry (e.g. `crontab(hour=3, minute=15)`, staggered from the existing 03:00 AI cleanup job).
- [ ] 2.4 Add a unit test for the cleanup task's `_cleanup` function verifying it deletes rows with `expires_at` in the past and leaves non-expired rows (revoked or not) untouched.
- [ ] 2.5 Manually verify: run the task against a local/dev DB with a manually-inserted expired session row, confirm it's deleted and non-expired rows remain.
- [ ] 2.6 Run worker-service tests and lint clean; PR merged (`Closes` the ticket).

## 3. Consolidate session issuance and remove verify_email's redundant query — independent of groups 1-2, may ship in any order

- [ ] 3.1 Add a shared session-issuance helper in `services/users/app/api/auth_routes.py` (refresh token → `create_session` → access-token claim assembly, built from an already-loaded `user` object) and switch `login()` and `refresh_token()` to use it, preserving their existing claims/response shape exactly.
- [ ] 3.2 Switch `verify_email()` to the same helper, passing the `user` returned by `mark_email_verified` — this removes its `_customer_role_claims(db, user.customer_id)` second DB query, since the helper reads `user.customer` directly like `login()` does.
- [ ] 3.3 Add/update unit tests asserting `login`, `refresh_token`, and `verify_email` issue tokens with identical claim sets for equivalent users (role, customer_id, is_ngo/is_donor flags, email_verified).
- [ ] 3.4 Run users-service tests and lint (flake8 --max-line-length=100) clean; PR merged (`Closes` the ticket).

## 4. Revoke pre-existing sessions when verify-email is reused for email-change confirmation — depends on group 3 (shares the same handler)

- [ ] 4.1 In `verify_email()`, before minting the new session, call `get_non_revoked_sessions_for_user(db, user.id)`; if it returns any sessions, revoke each via the existing `_revoke_session_everywhere` helper (same one `change_password()` uses) before issuing the new session.
- [ ] 4.2 Add a unit test: a user with an active session confirms an email change via `/auth/verify-email`; assert the prior session is revoked (both in Postgres and via the Redis mark) and only the new one is valid.
- [ ] 4.3 Add a unit test: a first-time (never-verified) account has no prior sessions, so verification proceeds without any revocation call.
- [ ] 4.4 Run users-service tests and lint clean; PR merged (`Closes` the ticket).

## 5. Frontend verification-flow polish — independent, may ship in any order

- [ ] 5.1 `frontend-typescript/src/pages/VerifyEmail.tsx`: pass `state={{ email }}` on the expired-link "Resend confirmation email" link, matching the convention Register.tsx/Login.tsx already use for navigations to `/confirm-email`, so the one recovery path from an expired verification link carries the email forward.
- [ ] 5.2 `frontend-typescript/src/pages/ConfirmEmail.tsx`: collapse the authenticated/unauthenticated JSX branches into one shared paragraph wrapper with only the differing action element (logout button vs. register-again link) varying.
- [ ] 5.3 Run frontend lint/typecheck clean; PR merged (`Closes` the ticket).
