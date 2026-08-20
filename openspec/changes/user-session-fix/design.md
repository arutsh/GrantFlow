## Context

`services/users` persists one `user_sessions` row per login (model: `services/users/app/models/session.py`, columns include `revoked: bool` and `expires_at`). The panel at `frontend-typescript/src/pages/Settings/components/SecuritySection.tsx` calls `GET /auth/sessions`, which is backed by `get_non_revoked_sessions_for_user` (`services/users/app/crud/sessions_curd.py:35-41`). That query filters only on `revoked == False` and ignores `expires_at`, so sessions that expired days/weeks ago still render as "active" until a user manually clicks Revoke. Nothing ever purges expired rows — the only existing cleanup job, `services/worker/tasks/ai/cleanup_sessions.py` (Celery beat, daily at 03:00 UTC), deletes rows from the unrelated `ai_chat_sessions` table on the AI service's own database.

One session row per login is intentional (the UI supports multiple simultaneous device sessions), so the original scope of this change was purely a listing-filter bug plus a missing hygiene job, not a session-issuance bug.

A code review of the companion `high-email-verification-fix` change (which added `verify_email()`'s own session-issuance block to `auth_routes.py`) found that the same file now has three independently maintained copies of "issue refresh token → create session row → mint access token with role/verified claims" (`login()`, `refresh_token()`, `verify_email()`), and that `verify_email()` never revokes a pre-existing session when the same endpoint is reused to confirm an email-change (`get_user_by_verification_token` matches `pending_email` too, so an already-authenticated user's email-change confirmation flows through this same handler). Both are session-lifecycle defects adjacent enough to this change's existing scope to fix together rather than opening a third change touching the same file.

## Goals / Non-Goals

**Goals:**
- The active-sessions panel only ever shows sessions that are both non-revoked and not yet expired.
- Expired `user_sessions` rows are eventually purged from the database so the table doesn't grow unbounded for users who never open the settings page.
- Session issuance in `auth_routes.py` has one implementation, not three, so a future claim change can't silently apply to only some of `login`/`refresh_token`/`verify_email`.
- `verify_email()` doesn't leave a pre-existing session alive in parallel with the new one when it's reused for the email-change confirmation flow.

**Non-Goals:**
- Changing `login()`'s or `refresh_token()`'s external request/response contract — the shared-issuance refactor is internal; both endpoints keep issuing exactly the claims they do today.
- Introducing a cap on concurrent sessions per user.
- Revoking other sessions automatically on a *new* login (would break legitimate multi-device use) — the new revoke-on-reuse behavior is scoped specifically to `verify_email()`'s email-change case, not to `login()`.

## Decisions

- **Filter fix**: add `SessionModel.expires_at > now(UTC)` to the `get_non_revoked_sessions_for_user` query. This is the minimal fix for the user-visible bug and ships independently of the cleanup job.
- **Cleanup job placement**: add a new worker task `tasks.users.cleanup_sessions`, following the exact pattern of `tasks.ai.cleanup_sessions` (module-level lazy-initialized engine, raw `DELETE ... WHERE expires_at < :cutoff RETURNING id`, registered in `celery_app.py`'s `include` list, routed via the existing `"tasks.users.*"` queue rule, and added to `beat_schedule`). Chosen over extending the AI cleanup task because it operates on a different service's database (`services/users`, not `services/ai`) and should stay isolated per service, matching the existing per-service task module layout (`tasks/ai/`, `tasks/users/`, `tasks/debug/`).
- **Retention window before delete**: purge sessions once `expires_at` has passed (no additional grace period) — the row's only purpose after expiry is historical audit, which isn't a current requirement. Alternative considered: keep a 30-day grace window like the AI cleanup task's `last_activity_at` cutoff; rejected because that task's grace period exists to bound *active* session count, whereas here `expires_at` already encodes the intended lifetime, so any additional delay just re-introduces the original bug's symptom (long-dead rows lingering) at a smaller scale.
- **Database connectivity for the new task**: `services/worker/config.py` currently only defines `AI_DATABASE_URL`. This change adds a `USERS_DATABASE_URL` setting to the worker config, mirroring the existing pattern, sourced from the same connection string `services/users` already uses.
- **Shared session-issuance helper**: add `_issue_session(db, user) -> TokenResponse`-shaped helper (name TBD at implementation) in `auth_routes.py` that does refresh-token creation, `create_session`, and access-token claim assembly in one place; `login()` and `refresh_token()` call it with their already-loaded `user`/`s.user`, and `verify_email()` calls it with the `user` returned by `mark_email_verified`. Because the helper always builds claims from a loaded `user.customer` (like `login()` already does), `verify_email()` no longer needs `_customer_role_claims(db, user.customer_id)`'s second DB fetch — that redundant query is removed as a side effect of the consolidation, not a separate change.
- **Revoke-on-reuse for `verify_email()`**: before minting the new session, check whether the account already has any non-revoked sessions (`get_non_revoked_sessions_for_user(db, user.id)`, the same query this change is already touching). If any exist, this is not the account's first verification — it's an email-change confirmation on an already-sessioned account — so revoke them via the existing `_revoke_session_everywhere` helper (already used by `change_password()` for the same "sensitive account action forces re-auth on other devices" reasoning) before issuing the new one. Chosen over trying to identify and revoke one specific "originating" session, because `verify_email()` is an unauthenticated endpoint (identified by email + token, no bearer token) — there is no reliable way to know which browser/tab initiated the request, so "revoke everything that was valid before this confirmation" is the only implementable and secure option, and is consistent with treating an email change as sensitive enough to warrant it.

## Risks / Trade-offs

- [New task touches `user_sessions` directly via raw SQL, bypassing the FastAPI service's ORM layer] → Mirrors the already-accepted pattern from `tasks.ai.cleanup_sessions`; low risk since the schema is stable and the delete is a single narrow predicate.
- [Adding `USERS_DATABASE_URL` to the worker duplicates a connection string already known to `services/users`] → Same duplication already exists for `AI_DATABASE_URL`; consistent with current architecture, not a new pattern.
- [Beat schedule cutover timing] → Cleanup runs daily at a fixed hour (proposed: 03:15 UTC, staggered from the existing 03:00 AI job to avoid both hitting the DB pool simultaneously); a user could still see a technically-expired-but-not-yet-purged session for up to 24h if the listing-filter fix weren't also shipped — mitigated because the filter fix (query-side) ships in the same change and is what actually controls what's visible, independent of purge timing.
- [Consolidating session issuance touches `login()` and `refresh_token()`, the two highest-traffic auth endpoints] → Refactor is behavior-preserving by construction (same claims, same response shape); mitigated by task 3's requirement that `login`/`refresh_token`/`verify_email` are asserted to issue identical claim sets for equivalent users before/after, not just "tests still pass."
- [Revoking sessions on email-change confirmation forces re-auth on every other device the user was logged in on] → Intentional: an email change is a primary-identifier change, similar in sensitivity to a password change, which already revokes other sessions (`change_password()`). A user who only ever has one session (the common case, and always true for first-time verification) sees no behavior change at all.
- [The one-time `revoke_unverified_sessions.py` rollout script (fixed separately, in `high-email-verification-fix`, for an unrelated N+1-query issue) still duplicates the "revoke + mark in Redis" pattern that `_revoke_session_everywhere`/`_revoke_user_sessions` also implement, rather than reusing it] → Accepted, not unified: that script now does a single bulk SQL `UPDATE` across all affected sessions for performance (it can run against an unbounded number of accounts during rollout), which the per-session helpers can't do without giving up that bulk-query win. Three implementations of the same intent is a known, deliberate trade-off, not an oversight — revisit only if a fourth caller needs the same logic.

## Migration Plan

1. Ship the query filter change to `get_non_revoked_sessions_for_user` (immediately fixes the visible bug, no schema/infra changes).
2. Add `USERS_DATABASE_URL` to worker config/env (all environments: local `.env`, deploy configs).
3. Add `tasks/users/cleanup_sessions.py`, register it in `celery_app.py`'s `include` and `beat_schedule`.
4. Deploy worker; verify the task runs on schedule and deletes only expired rows (spot-check via task result / logs).
5. Add the shared `_issue_session` helper and switch `login()`/`refresh_token()`/`verify_email()` to use it; ship independently of steps 1-4 (touches a different part of the same file, no ordering dependency).
6. Add the revoke-on-reuse check to `verify_email()`, after step 5 lands (it calls the same helper for issuance).
7. No rollback complexity: the filter change is a pure query addition (revert by removing the clause), the cleanup task can be disabled by removing its `beat_schedule` entry, and the issuance consolidation / revoke-on-reuse check are both revertible by reverting their respective commits without any data migration.

## Open Questions

- Exact purge cadence/hour — proposed daily at 03:15 UTC to stagger from the existing AI job; confirm no conflicting maintenance windows.
