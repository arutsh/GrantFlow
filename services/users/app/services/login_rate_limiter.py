from app.core.config import settings
from app.utils.redis import redis_client

# Generalized beyond login: verify-email takes the same class of
# attacker-guessable input (email + token) that this was built to defend
# login against, so it reuses the same Redis-backed lockout rather than a
# copy-pasted module — `bucket` just keeps the two counters from sharing a
# key space, since a login failure and a verify-email failure aren't the
# same signal.


def _key(bucket: str, scope: str, ident: str) -> str:
    return f"{bucket}_fail:{scope}:{ident}"


def is_locked_out(email: str, ip: str, *, bucket: str = "login") -> bool:
    """Fails open — a Redis outage degrades to no lockout rather than
    blocking every attempt."""
    if not redis_client:
        return False
    try:
        max_attempts = settings.LOGIN_MAX_ATTEMPTS
        acct_count = redis_client.get(_key(bucket, "acct", email.lower()))
        ip_count = redis_client.get(_key(bucket, "ip", ip))
        return (acct_count is not None and int(acct_count) >= max_attempts) or (
            ip_count is not None and int(ip_count) >= max_attempts
        )
    except Exception:
        return False


def record_failed_attempt(email: str, ip: str, *, bucket: str = "login") -> None:
    if not redis_client:
        return
    try:
        window = settings.LOGIN_LOCKOUT_SECONDS
        for key in (_key(bucket, "acct", email.lower()), _key(bucket, "ip", ip)):
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, window)
    except Exception:
        pass


def clear_failed_attempts(email: str, *, bucket: str = "login") -> None:
    """Only clears the account-scope counter — the ip-scope one must survive
    a successful login to still protect other accounts on the same IP."""
    if not redis_client:
        return
    try:
        redis_client.delete(_key(bucket, "acct", email.lower()))
    except Exception:
        pass
