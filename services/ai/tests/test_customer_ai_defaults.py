import anyio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.customer_ai_defaults import get, set_platform_fallback
from app.models.customer_ai_defaults import CustomerAiDefaults

CUSTOMER_ID = "cccccccc-0000-0000-0000-000000000003"


def _make_mock_db():
    return AsyncMock(spec=AsyncSession)


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class TestGet:
    def test_returns_none_when_no_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        result = anyio.run(get, CUSTOMER_ID, db)
        assert result is None


class TestSetPlatformFallback:
    def test_creates_row_when_none_exists(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = anyio.run(lambda: set_platform_fallback(CUSTOMER_ID, True, db))
        db.add.assert_called_once()
        assert result.platform_fallback_enabled is True

    def test_updates_existing_row(self):
        db = _make_mock_db()
        existing = CustomerAiDefaults()
        existing.customer_id = CUSTOMER_ID
        existing.platform_fallback_enabled = True
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = anyio.run(lambda: set_platform_fallback(CUSTOMER_ID, False, db))
        assert result is existing
        assert existing.platform_fallback_enabled is False
