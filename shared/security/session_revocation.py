import os

import redis

# Every service has its own Postgres database (see docker-compose*.yml —
# one `grandflow-db` instance, but a distinct database name per service), so
# shared/security (imported by every service) can't run a cross-service SQL
# lookup against the users-service's `user_sessions` table. Redis, by
# contrast, is one shared instance reachable from every service (same
# REDIS_URL host across services/*/.env.*), so it's the practical place for
# a revocation check that has to work from budget/ai/chat too, not just the
# users service itself. `SessionModel.revoked` in Postgres stays the
# source of truth (used for the active-sessions listing); this is a
# write-through cache of that fact for fast, cross-service enforcement.
_redis_client: "redis.Redis | None" = None
_REVOKED_KEY_PREFIX = "session:revoked:"


def _get_client() -> "redis.Redis | None":
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_client = redis.from_url(redis_url)
        except Exception:
            return None
    return _redis_client


def mark_session_revoked(session_id: str, ttl_seconds: int) -> None:
    """Best-effort: a failure here must not block the logout/revoke request
    that's already durably committed the revocation to Postgres."""
    client = _get_client()
    if not client:
        return
    try:
        client.setex(f"{_REVOKED_KEY_PREFIX}{session_id}", ttl_seconds, "1")
    except Exception:
        pass


def is_session_revoked(session_id: str) -> bool:
    """Fails open (treats Redis being unavailable as 'not revoked') —
    consistent with this codebase's existing rate-limiter fail-open
    policy (services/ai/app/services/rate_limiter.py): a Redis outage
    degrades revocation enforcement rather than taking down auth entirely."""
    if not session_id:
        return False
    client = _get_client()
    if not client:
        return False
    try:
        return bool(client.exists(f"{_REVOKED_KEY_PREFIX}{session_id}"))
    except Exception:
        return False
