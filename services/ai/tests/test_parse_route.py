import redis
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.config import settings
from main import app
from app.api.parse_routes import get_validated_user
from app.services.provider import get_resolved_model
from tests.factories.user import make_valid_user

client = TestClient(app)


class TestParseBudgetSync:
    @classmethod
    def setup_class(cls):
        app.dependency_overrides[get_validated_user] = make_valid_user

    @classmethod
    def teardown_class(cls):
        app.dependency_overrides.pop(get_validated_user, None)

    def test_null_provider_returns_ai_available_false(self):
        response = client.post("/api/v1/ai/parse-budget")
        assert response.status_code == 200
        assert response.json()["ai_available"] is False

    def test_requires_authentication(self):
        app.dependency_overrides = {}
        response = client.post("/api/v1/ai/parse-budget")
        assert response.status_code == 401
        app.dependency_overrides[get_validated_user] = make_valid_user


class TestParseBudgetStream:
    customer_id: str

    @classmethod
    def setup_class(cls):
        cls.customer_id = str(uuid4())
        app.dependency_overrides[get_validated_user] = lambda: make_valid_user(
            customer_id=cls.customer_id
        )

    @classmethod
    def teardown_class(cls):
        app.dependency_overrides.pop(get_validated_user, None)
        app.dependency_overrides.pop(get_resolved_model, None)
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.delete(f"rate_limit:ai:{cls.customer_id}")
            r.close()
        except Exception:
            pass

    def test_null_provider_stream_returns_unavailable_event(self):
        app.dependency_overrides[get_resolved_model] = lambda: None
        with patch(
            "app.services.rate_limiter.check_and_increment", new=AsyncMock(return_value=(True, 0))
        ):
            response = client.get("/api/v1/ai/parse-budget/stream?text=test")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: unavailable" in response.text

    def test_rate_limit_header_present_in_response(self):
        app.dependency_overrides[get_resolved_model] = lambda: None
        response = client.get("/api/v1/ai/parse-budget/stream?text=test")
        assert response.status_code == 200
        assert "x-ratelimit-limit" in response.headers

    def test_requires_authentication(self):
        app.dependency_overrides = {}
        response = client.get("/api/v1/ai/parse-budget/stream?text=test")
        assert response.status_code == 401
        app.dependency_overrides[get_validated_user] = lambda: make_valid_user(
            customer_id=self.customer_id
        )
