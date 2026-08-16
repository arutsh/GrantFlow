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
