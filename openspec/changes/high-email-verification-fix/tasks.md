Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Registration & verification core flow

- [x] 1.1 Remove session/token issuance from `register_endpoint` (`services/users/app/api/auth_routes.py`); return a minimal confirmation response instead of `TokenResponse`
- [x] 1.2 Update `verify_email_endpoint` to issue a new access token, refresh token, and session (`create_refresh_token`/`create_session`) on successful verification, returning them in the response
- [x] 1.3 Update the two `auth-hardening` "Registration Cannot Set Privileged Role" test scenarios to assert against the persisted `user.role` and the role claim of the session issued at verify-email, not a token returned by registration
- [x] 1.4 Frontend: registration submit no longer stores a token/logs in; show a static "check your email" confirmation page instead
- [x] 1.5 Frontend: `/verify-email` page consumes the access/refresh tokens now returned by the verify endpoint, logs the user in via `AuthContext`, and routes to the dashboard/onboarding on success
- [x] 1.6 Tests: registration issues no session; verify-email issues a valid session with `email_verified: true`; expired/already-used/invalid tokens still rejected as before
- [ ] 1.7 Run users-service test suite and flake8 (`--max-line-length=100`), and frontend test suite and lint, clean; PR merged

## 2. Anonymous, rate-limited resend-verification — depends on 1

- [x] 2.1 Drop `Depends(get_validated_user)` from `resend_verification_endpoint`; accept `email` in the request body instead
- [x] 2.2 Add a `resend_verification` rate-limit bucket keyed on combined `(email, client_ip)`, reusing the existing `is_locked_out`/`record_failed_attempt`/`clear_failed_attempts` pattern from `register_endpoint`
- [x] 2.3 Make the response identical in shape and content regardless of whether the account exists, is already verified, or is pending (generic "if that account exists, check your email" message); only issue a new token and enqueue an email for an existing, pending account
- [x] 2.4 Frontend: update the resend-verification call site to no longer require an authenticated session (e.g. usable directly from the "check your email" / confirm-email screens)
- [x] 2.5 Tests: resend works without auth for a pending account; resend for an already-verified or nonexistent email returns the same generic response and performs no token/email action; repeated requests past the threshold are rate-limited with 429
- [ ] 2.6 Run users-service test suite and flake8 clean, and frontend test suite and lint clean; PR merged

## 3. Login gating for unverified accounts — depends on 1, 2

- [x] 3.1 Update `login_endpoint` to check `user.email_verified` after credential validation; if false, skip session issuance and return a distinct, non-authenticating response directing the user to resend-verification
- [x] 3.2 Frontend: handle the new login response for unverified accounts — route to the confirm-email / resend screen instead of treating it as a login failure or a successful session
- [x] 3.3 Tests: login with correct credentials for an unverified account issues no session and returns the distinct response; login for a verified account is unchanged
- [ ] 3.4 Run users-service test suite and flake8 clean, and frontend test suite and lint clean; PR merged

## 4. Server-side session enforcement + rollout migration — depends on 1, 2, 3

- [x] 4.1 Update `get_validated_user` in `shared/security/dependencies.py` to reject tokens whose `email_verified` claim is not true, with a 403 response distinct from the existing 401 for invalid/expired/revoked tokens
- [x] 4.2 Confirm every current token-issuing path (login, refresh, verify-email) stamps `email_verified` from the account's current DB value at issuance time, not a stale/cached value
- [x] 4.3 Write a one-time rollout migration/script that revokes all existing sessions belonging to users with `email_verified = false`, using the same revocation mechanism as the logout endpoint
- [x] 4.4 Frontend: handle the new 403 `email_not_verified` response distinctly from 401 in the API client/interceptor (route to confirm-email rather than logging out / attempting silent refresh)
- [x] 4.5 Tests: a request with a valid but unverified token is rejected with 403 on a representative protected endpoint in each of users/budget/ai services (shared dependency, but verify it's actually wired the same way in each); a verified token behaves exactly as before
- [ ] 4.6 Manually verify the two known-affected accounts (`toby@sansome.org`, `avnikmelikian@gmail.com`) can complete verification via the group-2 resend flow post-rollout (once the underlying Mailjet outage is separately resolved)
- [ ] 4.7 Run affected services' test suites and flake8 clean, and frontend test suite and lint clean; PR merged
