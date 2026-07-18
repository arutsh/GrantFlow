import redis.asyncio as aioredis
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def check_and_increment(customer_id: str, limit: int | None = None) -> tuple[bool, int]:
    """Sliding window counter keyed by customer_id.

    Returns (allowed, retry_after_seconds). retry_after is 0 when allowed.
    Fails open if Redis is unavailable.
    """
    effective_limit = limit if limit is not None else settings.AI_RATE_LIMIT_PER_HOUR
    key = f"rate_limit:ai:{customer_id}"
    try:
        client = get_redis_client()
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 3600)
        if count > effective_limit:
            ttl = await client.ttl(key)
            return False, max(ttl, 0)
        return True, 0
    except Exception:
        logger.warning("rate_limiter_unavailable", customer_id=customer_id)
        return True, 0


async def enforce_rate_limit(customer_id: str, *, extra_headers: dict | None = None) -> None:
    """Raise 429 with a Retry-After header when the customer is over their hourly limit."""
    allowed, retry_after = await check_and_increment(customer_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after), **(extra_headers or {})},
        )
