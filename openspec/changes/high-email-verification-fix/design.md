## Context

`POST /register` currently creates the user and immediately issues a full access+refresh session (`services/users/app/api/auth_routes.py:107-166`), before the user has confirmed ownership of their email address. No API endpoint checks the `email_verified` JWT claim or user status — `shared/security/dependencies.py`'s `get_validated_user` (used by every service: budget, ai, chat, users) only validates signature, expiry, and session revocation. The frontend's `PrivateRoute` guard (`frontend-typescript/src/App.tsx:34-40`) is the only thing currently preventing an unverified account from reaching real data, and it is UI-only — a direct API call with the user's own token bypasses it entirely. Separately, `/auth/resend-verification` requires that same session (`Depends(get_validated_user)`), so a user whose 20-minute access token and 7-day refresh token both lapse before they act on their verification email has no self-serve recovery path.

This surfaced during investigation of a production incident where verification emails silently failed to send (unrelated Mailjet provider outage) — that outage is not part of this change; it exposed these pre-existing gaps rather than causing them.

## Goals / Non-Goals

**Goals:**
- No authenticated session exists for an account until its email is confirmed.
- `email_verified` is enforced server-side, at the single shared auth dependency, not just in the frontend.
- A user can always request a new verification link without needing an active session.
- Verification-link requests don't leak whether an email is registered or already verified.

**Non-Goals:**
- Fixing the Mailjet provider outage itself (separate ops issue, tracked outside this change).
- Changing the password-reset token flow (separate mechanism, not touched here).
- Building account lockout/abuse tooling beyond reusing the existing rate-limit pattern.
- Retroactively deciding whether invited users (`/auth/accept-invite`) should be treated as pre-verified — flagged as an open question, not resolved here.

## Decisions

**Login also returns no session for an unverified account.** The existing spec explicitly allowed unverified users to log in and receive a token (`email-verification` capability, "Login remains available to unverified users"), gating only the onboarding UI on the claim. That's incompatible with enforcing `email_verified` at `get_validated_user`: an unverified user's login would appear to succeed (200, token issued) but the token would be rejected on the very next authenticated call, which is a confusing dead end rather than a fix. `login_endpoint` is updated to check `user.email_verified` after credential validation and, if false, skip session issuance and return a distinct response pointing the user at resend-verification — consistent with registration's behavior rather than a special case of it.

**Registration returns no session.** `register_endpoint` drops the `create_refresh_token`/`create_session`/access-token issuance block entirely and returns a minimal confirmation (e.g. `{"message": "...", "email": ...}`) instead of `TokenResponse`. This is a **BREAKING** change to `/register`'s response contract. Alternative considered: keep issuing a token but scope it (a restricted "pre-verification" token type). Rejected — a second token type is more moving parts than removing the token, and the fail-closed property (no token = literally cannot call protected endpoints) is stronger than any scoping logic that has to be remembered and correctly enforced everywhere.

**`/auth/verify-email` becomes the session-issuing endpoint.** On successful token validation, in addition to setting `email_verified = true` (existing behavior), it now creates the refresh token + session and returns them, same shape as today's login response. This is the natural point to log the user in — it's the first moment identity is actually confirmed.

**`/auth/resend-verification` becomes anonymous.** Drops `Depends(get_validated_user)`, takes `email` in the request body. Rate-limited by combined `(email, client_ip)` key using the same `is_locked_out`/`record_failed_attempt` mechanism `/register` already uses (`auth_routes.py:116-120`), under a new bucket. Regardless of whether the account exists, is already verified, or is pending, the endpoint returns an identical generic response (e.g. "If that account exists and needs verification, we've sent a link") and takes the same code path length/shape internally, to avoid both user enumeration and timing-based enumeration. A real send is only enqueued for an existing, pending account.

**`get_validated_user` additionally requires `email_verified: true` in the JWT.** Single choke point (`shared/security/dependencies.py`), so every service inherits the check automatically. Returns 403 (not 401) with a distinct body (e.g. `{"detail": "email_not_verified"}`) — 401 conventionally means "not authenticated / go log in again," which would be wrong here since the token is otherwise valid; 403 lets the frontend distinguish "needs to verify" from "needs to log back in" without guessing from message text. Given registration no longer issues a session, this check should be unreachable in steady state — it exists as defense-in-depth against future code paths that (re-)introduce pre-verification tokens, and to close the gap for sessions issued before this change ships (see Migration Plan).

## Risks / Trade-offs

- **[Risk]** `/register`'s breaking response change requires the frontend deploy to land no earlier than the backend, or registration briefly breaks for new users mid-rollout. → Mitigation: this is a single-consumer API (only `frontend-typescript`); coordinate as one release rather than independent deploys.
- **[Risk]** Enforcing `email_verified` at `get_validated_user` could lock out already-verified users if their existing token's claim is stale or if any token-issuing path (e.g. the plain `/auth/login` endpoint) doesn't stamp `email_verified` correctly. → Mitigation: verify during implementation that `/auth/login` (not just register/verify-email) builds the claim from current `user.email_verified` at each login, not a cached/stale value.
- **[Risk]** Revoking sessions for currently-pending users at rollout logs out anyone mid-registration at deploy time. → Mitigation: acceptable — they weren't verified and couldn't reach sensitive data anyway; they self-recover via the now-anonymous resend endpoint with no data loss.
- **[Trade-off]** True constant-time enumeration resistance (matching response latency exactly regardless of DB hit) is not being built — only response *shape* is normalized. Residual timing side-channel is accepted as low-severity for this change.

## Migration Plan

1. Ship backend changes (`get_validated_user`, `resend-verification`, `verify-email`, `register`) and frontend changes together in one deploy.
2. As part of rollout, run a one-time revocation of sessions belonging to users with `email_verified = false`, so the server-side enforcement takes effect immediately rather than waiting up to 7 days for old refresh tokens to expire naturally. Exact mechanism (script vs. migration) to be determined in tasks — depends on the existing session-revocation primitive used by the logout endpoint.
3. The two known-affected accounts from the recent incident (`toby@sansome.org`, `avnikmelikian@gmail.com`) verify themselves through the new anonymous resend flow post-rollout; no manual token generation needed.
4. Rollback: revert the deploy. No irreversible data migration is involved — revoked sessions simply require affected pending users to log in again via resend, which they'd need to do anyway.

## Open Questions

- Should `/auth/accept-invite` treat the invited user as pre-verified (since the admin already sent the invite to a specific address, and acceptance implies delivery)? Needs a decision before implementation touches the invite flow — if unresolved, leave invite-accept behavior untouched and out of scope for this change.
- Exact primitive for bulk-revoking sessions by user (does one already exist, or does logout only revoke the caller's own session)?
