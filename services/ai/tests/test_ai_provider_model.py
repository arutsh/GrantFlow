import anyio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.ai_provider_model import exists_for_provider

PROVIDER_ID = "bbbbbbbb-0000-0000-0000-000000000002"


def _make_mock_db():
    return AsyncMock(spec=AsyncSession)


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class TestExistsForProvider:
    def test_returns_true_when_model_belongs_to_provider(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result("some-id"))
        result = anyio.run(exists_for_provider, PROVIDER_ID, "claude-sonnet-4-6", db)
        assert result is True

    def test_returns_false_when_model_not_registered_for_provider(self):
        """claude-haiku-4-5 must not validate against the ollama provider."""
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        result = anyio.run(exists_for_provider, PROVIDER_ID, "claude-haiku-4-5", db)
        assert result is False
