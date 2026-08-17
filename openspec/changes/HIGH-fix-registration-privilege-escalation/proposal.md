## Why

**CRITICAL, exploit confirmed against local dev.** `POST /api/register` accepts a client-supplied `role` with no server-side validation. Any anonymous caller can register with `"role": "superuser"`, receive a valid JWT carrying that claim, and pass it straight through the `role == "superuser"` guard on `POST /api/auth/impersonate` to mint an admin token for any `customer_id` — full cross-tenant data access, no prior account or authorization needed. Verified end-to-end: registered as `superuser`, impersonated an arbitrary customer, pulled that tenant's private budget data from the budget service. This also violates the `company-onboarding` spec's existing invariant that "the registration default[ is] `user`" and that no self-service path grants `superuser` — the code has drifted out of sync with that assumption. Must be fixed before `customer-impersonation` (openspec/changes/superuser-cross-tenant-access) ships, since that feature's authorization model assumes `role` in the JWT is trustworthy.

Two related weaknesses surfaced in the same pentest: `/api/register` has no rate limiting (unlike login/verify-email/change-password), and it leaks account existence via a distinct "Email already registered" error.

## What Changes

- Remove the client-supplied `role` field from registration — the server always creates new accounts as `role: user`, ignoring any `role` in the request body. Escalation to `admin`/`superuser` remains possible only through the existing protected admin-management endpoints and the `company-onboarding` promotion path.
- Add a DB-level CHECK constraint on `UserModel.role` restricting it to `superuser`/`admin`/`user`, as defense in depth against any future code path that assigns role from unvalidated input.
- Apply the existing login-rate-limiter mechanism (`is_locked_out`/`record_failed_attempt`) to `POST /api/register`, keyed per source IP.
- **BREAKING**: `RegisterRequest.role` and `RegisterRequest.customer_id`-plus-arbitrary-`role` combination is no longer honored by the API — any caller currently relying on setting `role` at registration (there should be none in legitimate use, since `company-onboarding` already documents `user` as the registration default) will silently get `user` instead.

## Capabilities

### Modified Capabilities
- `auth-hardening`: adds requirements that registration SHALL ignore client-supplied `role`, SHALL rate-limit registration attempts per source IP, and SHALL NOT reveal via error message whether an email is already registered.

## Impact

- `shared/schemas/auth_schema.py` (`RegisterRequest`) — drop or ignore `role` field.
- `services/users/app/crud/user_crud.py` (`create_user`) — stop accepting caller-supplied `role`, or hardcode `UserRole.user` for the registration call site specifically.
- `services/users/app/api/auth_routes.py` (`register_endpoint`) — wire in rate limiting via `app/services/login_rate_limiter.py`; adjust duplicate-email error handling.
- `services/users/app/models/user.py` (`UserModel.role`) — add DB CHECK constraint; new Alembic migration required.
- Existing tests covering `/api/register` with an explicit `role` in the payload will need updating.
