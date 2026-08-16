## Why

The "Active sessions" panel in account security settings lists sessions that are long expired, and every login leaves a permanent new row behind instead of superseding prior logins from the same device. Users see dozens of stale "Other device" entries they must manually revoke one by one, and cannot tell which sessions are actually still valid. This violates the intent of the existing `session-security` capability's "Active Session Visibility" requirement, which implies the list reflects genuinely active sessions.

## What Changes

- `GET /auth/sessions` filters out sessions past their `expires_at` in addition to `revoked`, so expired sessions no longer appear as "active." (Login itself is unchanged — one row per login is correct, since the panel intentionally supports multiple simultaneous device sessions.)
- Add a scheduled cleanup task (mirroring the existing pattern in `services/worker/tasks/ai/cleanup_sessions.py`) that periodically deletes `user_sessions` rows past `expires_at`, so the table doesn't grow unbounded for users who never revisit the settings page to revoke old entries.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `session-security`: "Active Session Visibility" requirement is clarified so the listed sessions are limited to those that are both non-revoked AND not expired; adds a new requirement that expired session records are purged rather than retained indefinitely.

## Impact

- `services/users/app/api/auth_routes.py` (`list_sessions`)
- `services/users/app/crud/sessions_curd.py` (`get_non_revoked_sessions_for_user`, new purge query)
- `services/worker/tasks/` (new cleanup task) and its Celery beat schedule registration
- No breaking API contract changes: `GET /auth/sessions` response shape is unchanged, only which rows are included.
