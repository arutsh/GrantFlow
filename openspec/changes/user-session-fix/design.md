## Context

`services/users` persists one `user_sessions` row per login (model: `services/users/app/models/session.py`, columns include `revoked: bool` and `expires_at`). The panel at `frontend-typescript/src/pages/Settings/components/SecuritySection.tsx` calls `GET /auth/sessions`, which is backed by `get_non_revoked_sessions_for_user` (`services/users/app/crud/sessions_curd.py:35-41`). That query filters only on `revoked == False` and ignores `expires_at`, so sessions that expired days/weeks ago still render as "active" until a user manually clicks Revoke. Nothing ever purges expired rows — the only existing cleanup job, `services/worker/tasks/ai/cleanup_sessions.py` (Celery beat, daily at 03:00 UTC), deletes rows from the unrelated `ai_chat_sessions` table on the AI service's own database.

One session row per login is intentional (the UI supports multiple simultaneous device sessions), so this is not a session-issuance bug — it's a listing-filter bug plus a missing hygiene job.

## Goals / Non-Goals

**Goals:**
- The active-sessions panel only ever shows sessions that are both non-revoked and not yet expired.
- Expired `user_sessions` rows are eventually purged from the database so the table doesn't grow unbounded for users who never open the settings page.

**Non-Goals:**
- Changing login/refresh behavior or session issuance semantics.
- Introducing a cap on concurrent sessions per user.
- Revoking other sessions automatically on new login (would break legitimate multi-device use).

## Decisions

- **Filter fix**: add `SessionModel.expires_at > now(UTC)` to the `get_non_revoked_sessions_for_user` query. This is the minimal fix for the user-visible bug and ships independently of the cleanup job.
- **Cleanup job placement**: add a new worker task `tasks.users.cleanup_sessions`, following the exact pattern of `tasks.ai.cleanup_sessions` (module-level lazy-initialized engine, raw `DELETE ... WHERE expires_at < :cutoff RETURNING id`, registered in `celery_app.py`'s `include` list, routed via the existing `"tasks.users.*"` queue rule, and added to `beat_schedule`). Chosen over extending the AI cleanup task because it operates on a different service's database (`services/users`, not `services/ai`) and should stay isolated per service, matching the existing per-service task module layout (`tasks/ai/`, `tasks/users/`, `tasks/debug/`).
- **Retention window before delete**: purge sessions once `expires_at` has passed (no additional grace period) — the row's only purpose after expiry is historical audit, which isn't a current requirement. Alternative considered: keep a 30-day grace window like the AI cleanup task's `last_activity_at` cutoff; rejected because that task's grace period exists to bound *active* session count, whereas here `expires_at` already encodes the intended lifetime, so any additional delay just re-introduces the original bug's symptom (long-dead rows lingering) at a smaller scale.
- **Database connectivity for the new task**: `services/worker/config.py` currently only defines `AI_DATABASE_URL`. This change adds a `USERS_DATABASE_URL` setting to the worker config, mirroring the existing pattern, sourced from the same connection string `services/users` already uses.

## Risks / Trade-offs

- [New task touches `user_sessions` directly via raw SQL, bypassing the FastAPI service's ORM layer] → Mirrors the already-accepted pattern from `tasks.ai.cleanup_sessions`; low risk since the schema is stable and the delete is a single narrow predicate.
- [Adding `USERS_DATABASE_URL` to the worker duplicates a connection string already known to `services/users`] → Same duplication already exists for `AI_DATABASE_URL`; consistent with current architecture, not a new pattern.
- [Beat schedule cutover timing] → Cleanup runs daily at a fixed hour (proposed: 03:15 UTC, staggered from the existing 03:00 AI job to avoid both hitting the DB pool simultaneously); a user could still see a technically-expired-but-not-yet-purged session for up to 24h if the listing-filter fix weren't also shipped — mitigated because the filter fix (query-side) ships in the same change and is what actually controls what's visible, independent of purge timing.

## Migration Plan

1. Ship the query filter change to `get_non_revoked_sessions_for_user` (immediately fixes the visible bug, no schema/infra changes).
2. Add `USERS_DATABASE_URL` to worker config/env (all environments: local `.env`, deploy configs).
3. Add `tasks/users/cleanup_sessions.py`, register it in `celery_app.py`'s `include` and `beat_schedule`.
4. Deploy worker; verify the task runs on schedule and deletes only expired rows (spot-check via task result / logs).
5. No rollback complexity: the filter change is a pure query addition (revert by removing the clause), and the cleanup task can be disabled by removing its `beat_schedule` entry without affecting request-serving paths.

## Open Questions

- Exact purge cadence/hour — proposed daily at 03:15 UTC to stagger from the existing AI job; confirm no conflicting maintenance windows.
