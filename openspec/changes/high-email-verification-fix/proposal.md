## Why

Registration currently issues a full-scope, authenticated session before the user's email is confirmed, and no API endpoint checks verification status server-side — only the frontend route guard does. A user was observed reaching the dashboard for an unverified account, and independently, `/auth/resend-verification` requires that same session, so a user whose access/refresh token has expired before they act on their verification email has no self-serve way to get a new link. Both stem from treating "has a session" as equivalent to "owns this email," which they are not. Given a recent production incident where verification email delivery silently failed, this is being fixed now while the failure mode is fresh and before it's exploited.

## What Changes

- **BREAKING**: `/register` no longer issues an access/refresh token or session. It creates the pending user and returns a non-authenticating confirmation response.
- **BREAKING**: `/auth/login` no longer issues a session for an account whose email is still unverified (e.g. someone who registered previously and never confirmed). It returns a distinct response directing them to request a new verification link, instead of issuing a token that would be rejected on every subsequent call anyway.
- `/auth/resend-verification` becomes an unauthenticated, email-based endpoint, rate-limited by email+IP (reusing the existing lockout pattern from `/register`), always returning a generic response regardless of account existence or current verification state (prevents enumeration).
- `/auth/verify-email` now issues the first access/refresh token pair and session on successful verification — this becomes the actual login moment for a new registration.
- `shared/security/dependencies.py`'s `get_validated_user` additionally rejects tokens for users whose `email_verified` claim is false, as defense-in-depth against any other pre-verification token issuance path and against sessions already outstanding from before this fix ships.
- Frontend: registration flow shows a static "check your email" confirmation instead of landing in an authenticated shell; `/verify-email` handles the token response and logs the user in on success.
- Existing sessions for currently-pending users are proactively revoked as part of rollout so the fix takes effect immediately rather than waiting up to 7 days for old refresh tokens to expire.

## Capabilities

### New Capabilities
(none — this modifies existing auth behavior, not new capability surface)

### Modified Capabilities
- `email-verification`: registration no longer issues a session; `/auth/verify-email` issues the first session on success; resend-verification becomes unauthenticated and enumeration-safe.
- `session-security`: session authentication additionally requires `email_verified: true`; sessions held by pending (unverified) users are revoked at rollout.
- `auth-hardening`: resend-verification gains per-email+IP rate limiting, matching the existing registration lockout pattern.

## Impact

- **Backend (users service)**: `services/users/app/api/auth_routes.py` (`register_endpoint`, `login_endpoint`, `resend_verification_endpoint`, `verify_email_endpoint`), `services/users/app/crud/user_crud.py`.
- **Shared**: `shared/security/dependencies.py` (`get_validated_user`) — affects every service (budget, ai, chat, users) that depends on it for auth.
- **Frontend**: registration and verify-email pages/flows, `AuthContext`, `PrivateRoute` (`frontend-typescript/src`).
- **Data/session**: one-time revocation of existing sessions belonging to pending (unverified) users at rollout.
- **Two known-affected accounts** (`toby@sansome.org`, `avnikmelikian@gmail.com`) from the recent incident should complete verification through the new resend flow once shipped, rather than via manual token generation.
