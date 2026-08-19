## Why

The "Active sessions" panel in account security settings lists sessions that are long expired, and every login leaves a permanent new row behind instead of superseding prior logins from the same device. Users see dozens of stale "Other device" entries they must manually revoke one by one, and cannot tell which sessions are actually still valid. This violates the intent of the existing `session-security` capability's "Active Session Visibility" requirement, which implies the list reflects genuinely active sessions.

A code review of the companion email-verification change (`high-email-verification-fix`) surfaced three further session-lifecycle gaps in the same area of `services/users/app/api/auth_routes.py` that are cheapest to fix alongside this one: session issuance (refresh token → session row → access-token claims) is now independently duplicated across `login()`, `refresh_token()`, and `verify_email()`, risking claim drift between them; `verify_email()` re-fetches the customer record via a second DB query even though it's already loaded on the `user` object, an avoidable query on what is now effectively the account's first-login path; and `verify_email()` mints a brand-new session without revoking whichever session(s) were already active when the same endpoint is reused for the email-change/rectification flow, so old sessions accumulate with no cleanup path — the inverse problem of the stale-listing bug above, but on the issuance side instead of the display side. Two small frontend gaps in the same verification UI are included as opportunistic cleanup: the expired-link "Resend" action on `VerifyEmail.tsx` doesn't carry the typed email as router state the way Register/Login do, and `ConfirmEmail.tsx` duplicates its authenticated/unauthenticated JSX wrapper.

## What Changes

- `GET /auth/sessions` filters out sessions past their `expires_at` in addition to `revoked`, so expired sessions no longer appear as "active." (Login itself is unchanged — one row per login is correct, since the panel intentionally supports multiple simultaneous device sessions.)
- Add a scheduled cleanup task (mirroring the existing pattern in `services/worker/tasks/ai/cleanup_sessions.py`) that periodically deletes `user_sessions` rows past `expires_at`, so the table doesn't grow unbounded for users who never revisit the settings page to revoke old entries.
- Consolidate session issuance in `auth_routes.py` behind one shared helper used by `login()`, `refresh_token()`, and `verify_email()`, and have it build claims from an already-loaded `user.customer` instead of `verify_email()`'s redundant second query.
- `verify_email()` revokes the account's pre-existing active session(s) before issuing the new one whenever it's reused for the email-change/rectification flow (i.e. the account already had a session before this call), mirroring the existing revoke-other-sessions pattern in `change_password()`.
- Frontend polish: `VerifyEmail.tsx`'s expired-link resend action carries `state={{ email }}`; `ConfirmEmail.tsx`'s duplicated authenticated/unauthenticated JSX wrapper is collapsed to one shared wrapper.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `session-security`: "Active Session Visibility" requirement is clarified so the listed sessions are limited to those that are both non-revoked AND not expired; adds a new requirement that expired session records are purged rather than retained indefinitely; adds a new requirement that a pre-existing session is revoked when `/auth/verify-email` is reused to confirm an email change on an already-sessioned account.

## Impact

- `services/users/app/api/auth_routes.py` (`list_sessions`, `login`, `refresh_token`, `verify_email` — new shared `_issue_session` helper, revoke-on-reuse behavior)
- `services/users/app/crud/sessions_curd.py` (`get_non_revoked_sessions_for_user`, new purge query)
- `services/worker/tasks/` (new cleanup task) and its Celery beat schedule registration
- `frontend-typescript/src/pages/VerifyEmail.tsx`, `frontend-typescript/src/pages/ConfirmEmail.tsx` (no behavior contract change, UI-only)
- No breaking API contract changes: `GET /auth/sessions` response shape is unchanged, only which rows are included; `verify_email`'s response shape is unchanged, only its session-revocation side effect is new.
