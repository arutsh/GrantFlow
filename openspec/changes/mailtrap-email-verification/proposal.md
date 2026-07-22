## Why

Today `POST /register` in the users service creates an account in `UserStatus.pending` and the frontend sends the user straight to `/onboarding` without ever confirming they own the email address they signed up with. Anyone can register using someone else's email, there's no way to recover from a typo'd address, and we have no transactional-email capability in the codebase at all. Gating onboarding behind a confirmed email closes that gap and gives us the email-sending infrastructure future notifications will also need.

## What Changes

- Add a transactional email client wrapping the Mailtrap Sending API (token/config driven, no provider code exists in the repo today).
- On registration, generate a single-use, expiring verification token and send a confirmation email via Mailtrap **asynchronously** through the existing (currently unused) `tasks.users.*` Celery queue in `services/worker`, instead of blocking the request thread.
- Add `POST /auth/verify-email` (consumes the token) and `POST /auth/resend-verification` endpoints to the users service.
- Add an `email_verified` flag to the `User` model/schema, distinct from the existing `status` (active/pending/disabled) enum, and include it as a JWT claim alongside the existing `is_ngo`/`is_donor` role flags.
- **BREAKING**: Gate the onboarding flow — a user whose token does not carry `email_verified: true` is redirected to a "confirm your email" screen instead of `/onboarding`, until they click the link or complete verification.
- Frontend: add a post-registration "check your email" screen, a `/verify-email` landing route that consumes the token from the emailed link, and a resend-confirmation action; update `Register.tsx`/`Login.tsx` redirect logic to respect the new gate.

## Capabilities

### New Capabilities
- `email-verification`: registration-time confirmation emails (via Mailtrap), token verification/resend endpoints, the `email_verified` user state and JWT claim, and the onboarding gate that depends on it.

### Modified Capabilities
- None — `openspec/specs/` has no existing capability specs yet, so there is nothing to modify; this change establishes the first one.

## Impact

- **services/users**: `app/models/user.py` (new `email_verified` field + verification token storage), `app/crud/user_crud.py`, `app/api/auth_routes.py` (new endpoints, updated claims helper, registration flow), config for `MAILTRAP_API_TOKEN`/sender address.
- **shared/schemas/user_schema.py**: schema updates for the new field.
- **shared/security/jwt_utils.py** / claims helpers in `auth_routes.py`: add `email_verified` to the token payload alongside `is_ngo`/`is_donor`.
- **services/worker**: new Celery task under the existing `tasks.users` queue to send the verification email via Mailtrap; new dependency on a Mailtrap SDK/HTTP client.
- **frontend-typescript**: `Register.tsx`, `Login.tsx`, `OnBoarding.tsx`/`App.tsx` routing, new verify-email page and "check your email" screen, corresponding API calls.
- **New environment variables**: Mailtrap API token and sender identity, added to service env config (values themselves are not committed).
- **Database**: migration for the new `email_verified` column (and verification token/expiry storage) on the users table.
