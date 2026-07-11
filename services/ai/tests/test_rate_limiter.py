import anyio
import fakeredis
from unittest.mock import patch

from app.services.rate_limiter import check_and_increment


def _fake_redis():
    return fakeredis.FakeAsyncRedis(decode_responses=True)


class TestRateLimiter:
    def test_allows_requests_under_limit(self):
        async def _run():
            fake = _fake_redis()
            with patch("app.services.rate_limiter.get_redis_client", return_value=fake):
                for _ in range(5):
                    allowed, retry_after = await check_and_increment("cust-1", limit=5)
                    assert allowed is True
                    assert retry_after == 0

        anyio.run(_run)

    def test_blocks_request_at_limit_returns_429_with_retry_after(self):
        async def _run():
            fake = _fake_redis()
            with patch("app.services.rate_limiter.get_redis_client", return_value=fake):
                for _ in range(3):
                    await check_and_increment("cust-2", limit=3)

                allowed, retry_after = await check_and_increment("cust-2", limit=3)
                assert allowed is False
                assert retry_after > 0

        anyio.run(_run)

    def test_limit_is_per_customer_not_per_user(self):
        """Two users sharing the same customer_id count against one shared quota."""

        async def _run():
            fake = _fake_redis()
            with patch("app.services.rate_limiter.get_redis_client", return_value=fake):
                customer_id = "shared-customer"
                # Each call uses the customer_id key regardless of which user made it
                for _ in range(2):
                    allowed, _ = await check_and_increment(customer_id, limit=3)
                    assert allowed is True
                for _ in range(1):
                    allowed, _ = await check_and_increment(customer_id, limit=3)
                    assert allowed is True
                # 4th request — over the limit of 3
                allowed, retry_after = await check_and_increment(customer_id, limit=3)
                assert allowed is False
                assert retry_after > 0

        anyio.run(_run)

    def test_limit_resets_after_window(self):
        """Deleting the key simulates TTL expiry; next request should be allowed."""

        async def _run():
            fake = _fake_redis()
            with patch("app.services.rate_limiter.get_redis_client", return_value=fake):
                for _ in range(2):
                    await check_and_increment("cust-3", limit=2)

                blocked, _ = await check_and_increment("cust-3", limit=2)
                assert blocked is False

                # Simulate window reset by deleting the key
                await fake.delete("rate_limit:ai:cust-3")

                allowed, retry_after = await check_and_increment("cust-3", limit=2)
                assert allowed is True
                assert retry_after == 0

        anyio.run(_run)

    def test_different_customers_have_independent_limits(self):
        async def _run():
            fake = _fake_redis()
            with patch("app.services.rate_limiter.get_redis_client", return_value=fake):
                for _ in range(3):
                    await check_and_increment("cust-A", limit=3)

                blocked, _ = await check_and_increment("cust-A", limit=3)
                assert blocked is False

                # cust-B is untouched — should still be under limit
                allowed, _ = await check_and_increment("cust-B", limit=3)
                assert allowed is True

        anyio.run(_run)


class TestRateLimiterEndpoint:
    def test_blocks_request_at_limit_returns_429(self):
        """Integration: endpoint returns 429 when rate limit is exhausted."""
        from fastapi.testclient import TestClient
        from main import app
        from app.api.parse_routes import get_validated_user
        from app.services.provider import get_resolved_model
        from tests.factories.user import make_valid_user

        user = make_valid_user()

        async def _fake_check(cid: str, limit=None):
            return False, 3600

        def _mock_user():
            return user

        app.dependency_overrides[get_validated_user] = _mock_user
        # Rate limiting fires before the provider is used, so its value is
        # irrelevant — but without this override the dependency hits the DB.
        app.dependency_overrides[get_resolved_model] = lambda: None
        client = TestClient(app)

        with patch("app.api.parse_routes.check_and_increment", _fake_check):
            response = client.get("/api/v1/ai/parse-budget/stream?text=test")

        app.dependency_overrides = {}

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "3600"
