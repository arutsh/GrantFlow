One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Close the privilege-escalation hole: registration ignores client role, gets rate-limited

- [x] 1.1 Remove the `role` field from `RegisterRequest` in `shared/schemas/auth_schema.py` (imported into `services/users/app/schemas/auth_schema.py`)
- [x] 1.2 Update `register_endpoint` in `services/users/app/api/auth_routes.py` to call `create_user()` without forwarding a client role — always resulting in `role: user` for new accounts
- [x] 1.3 Confirm `create_user()` in `services/users/app/crud/user_crud.py` still accepts an explicit `role` kwarg for its other caller (admin-management/invite flow) — do not change its signature or default, only stop `register_endpoint` from passing a client-controlled value
- [x] 1.4 Wire `POST /api/register` into the existing `is_locked_out`/`record_failed_attempt` rate limiter (`app/services/login_rate_limiter.py`), keyed per source IP only, using a new `"register"` bucket, mirroring the pattern already used for `verify-email`/`change-password`
- [x] 1.5 Grep `frontend-typescript` for any registration form submitting a `role` field to `/api/register`; remove it if present (confirmed none — `Register.tsx` never sends `role`)
- [x] 1.6 Add/update tests: registering with `role: "superuser"` or `role: "admin"` in the payload results in a stored/JWT role of `user`; repeated registration attempts from one IP past the threshold return 429
- [x] 1.7 Re-run the exploit chain from the pentest (register with `role: superuser` → call `/auth/impersonate`) and confirm it now fails at step one — covered by an automated test (`test_registered_role_user_cannot_self_authorize_impersonation`) rather than a manual curl session against a running server
- [x] 1.8 Run the users-service test suite and lint clean; PR merged (`Closes` the tracking ticket)

## 2. Defense in depth: DB-level CHECK constraint on `users.role` — depends on 1

- [x] 2.1 Run a read-only audit query (`SELECT DISTINCT role FROM users`) against a production-equivalent dataset to confirm no existing row holds a value outside `superuser`/`admin`/`user`. *(Ran against local dev DB: only `superuser`/`admin`/`user` present.)*
- [x] 2.2 Write an Alembic migration adding a CHECK constraint on `users.role` restricting it to `superuser`, `admin`, `user`. *(Already done — discovered during implementation that migrations `000002_add_user_role_check_constraint` and `000003_add_admin_role` (merged in #81, "Phase 6: BYOK + admin role...", 2026-06-22/24) already add exactly this constraint: `CHECK (role IN ('superuser', 'admin', 'user'))`. Predates this change; no new migration needed.)*
- [x] 2.3 Apply the migration locally and confirm a direct INSERT/UPDATE with an invalid role value is rejected by the database. *(Confirmed on local dev DB: `UPDATE users SET role = 'manager' ...` raises `psycopg2.errors.CheckViolation: ... violates check constraint "users_role_check"`.)*
- [x] 2.4 Run the users-service test suite and migration checks clean; PR merged (`Closes` the tracking ticket). *(127 passed, flake8 --max-line-length=100 clean, `alembic current` at head `000009` with no pending migrations. No code change was needed for this group, so there is nothing to open a new PR for — group 1's already-merged PR is the closing PR for this ticket.)*
