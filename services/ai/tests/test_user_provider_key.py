import anyio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user_provider_key import delete_key, get_active_key_for_customer, get_key, upsert_key
from app.models.user_provider_key import UserProviderKey

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
CUSTOMER_ID = "cccccccc-0000-0000-0000-000000000003"
PROVIDER_ID = "bbbbbbbb-0000-0000-0000-000000000002"


def _make_mock_db():
    return AsyncMock(spec=AsyncSession)


def _scalar_result(value):
    result = MagicMock()
    result.unique.return_value.scalar_one_or_none.return_value = value
    return result


def _scalars_first_result(value):
    result = MagicMock()
    result.unique.return_value.scalars.return_value.first.return_value = value
    return result


class TestGetKey:
    def test_returns_none_when_no_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        result = anyio.run(get_key, USER_ID, PROVIDER_ID, db)
        assert result is None

    def test_returns_row_when_found(self):
        db = _make_mock_db()
        row = UserProviderKey()
        row.user_id = USER_ID
        row.provider_id = PROVIDER_ID
        row.encrypted_key = "enc_value"
        db.execute = AsyncMock(return_value=_scalar_result(row))
        result = anyio.run(get_key, USER_ID, PROVIDER_ID, db)
        assert result is row


class TestGetActiveKeyForCustomer:
    def test_returns_none_when_no_key(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalars_first_result(None))
        result = anyio.run(get_active_key_for_customer, CUSTOMER_ID, db)
        assert result is None

    def test_returns_row_with_encrypted_key(self):
        db = _make_mock_db()
        row = UserProviderKey()
        row.customer_id = CUSTOMER_ID
        row.encrypted_key = "enc_value"
        db.execute = AsyncMock(return_value=_scalars_first_result(row))
        result = anyio.run(get_active_key_for_customer, CUSTOMER_ID, db)
        assert result is row


class TestUpsertKey:
    def test_inserts_when_no_existing_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        anyio.run(upsert_key, USER_ID, PROVIDER_ID, "enc_key", "claude-sonnet-4-6", None, db)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    def test_updates_when_row_exists(self):
        db = _make_mock_db()
        existing = UserProviderKey()
        existing.encrypted_key = "old_key"
        existing.model_name = "llama3.2"
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        anyio.run(upsert_key, USER_ID, PROVIDER_ID, "new_key", "claude-sonnet-4-6", None, db)
        assert existing.encrypted_key == "new_key"
        assert existing.model_name == "claude-sonnet-4-6"
        db.commit.assert_awaited_once()


class TestDeleteKey:
    def test_sets_encrypted_key_to_none(self):
        db = _make_mock_db()
        existing = UserProviderKey()
        existing.encrypted_key = "some_key"
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        db.commit = AsyncMock()

        anyio.run(delete_key, USER_ID, PROVIDER_ID, db)
        assert existing.encrypted_key is None
        db.commit.assert_awaited_once()

    def test_no_op_when_no_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        db.commit = AsyncMock()

        anyio.run(delete_key, USER_ID, PROVIDER_ID, db)
        db.commit.assert_not_awaited()
