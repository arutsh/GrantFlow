import anyio
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user_provider_key import (
    create,
    delete,
    get_active_key_for_customer,
    get_by_id,
    list_for_customer,
    set_default,
)
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


def _scalars_all_result(values):
    result = MagicMock()
    result.unique.return_value.scalars.return_value.all.return_value = values
    return result


def _config(config_id="id-1", is_default=False):
    row = UserProviderKey()
    row.id = config_id
    row.customer_id = CUSTOMER_ID
    row.provider_id = PROVIDER_ID
    row.is_default = is_default
    return row


class TestGetById:
    def test_returns_none_when_no_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        result = anyio.run(get_by_id, CUSTOMER_ID, "id-1", db)
        assert result is None

    def test_returns_row_when_found(self):
        db = _make_mock_db()
        row = _config()
        db.execute = AsyncMock(return_value=_scalar_result(row))
        result = anyio.run(get_by_id, CUSTOMER_ID, "id-1", db)
        assert result is row


class TestListForCustomer:
    def test_returns_all_configs_for_multiple_providers(self):
        """A customer can save more than one config for the same provider."""
        db = _make_mock_db()
        rows = [_config("id-1"), _config("id-2")]
        db.execute = AsyncMock(return_value=_scalars_all_result(rows))
        result = anyio.run(list_for_customer, CUSTOMER_ID, db)
        assert result == rows


class TestGetActiveKeyForCustomer:
    def test_returns_none_when_no_default(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        result = anyio.run(get_active_key_for_customer, CUSTOMER_ID, db)
        assert result is None

    def test_returns_the_default_row_not_most_recent(self):
        """Resolution uses is_default, not recency."""
        db = _make_mock_db()
        default_row = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalar_result(default_row))
        result = anyio.run(get_active_key_for_customer, CUSTOMER_ID, db)
        assert result is default_row


class TestCreate:
    def test_second_config_for_same_provider_is_added_not_overwritten(self):
        db = _make_mock_db()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        anyio.run(
            create,
            CUSTOMER_ID,
            USER_ID,
            PROVIDER_ID,
            "second key",
            "enc_key",
            "claude-sonnet-4-6",
            None,
            False,
            db,
        )
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    def test_creating_as_default_unsets_previous_default(self):
        db = _make_mock_db()
        previous_default = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalar_result(previous_default))
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        anyio.run(
            create,
            CUSTOMER_ID,
            USER_ID,
            PROVIDER_ID,
            "new default",
            "enc_key",
            "claude-sonnet-4-6",
            None,
            True,
            db,
        )
        assert previous_default.is_default is False


class TestSetDefault:
    def test_switching_default_unsets_previous_and_sets_new(self):
        db = _make_mock_db()
        target = _config("id-2", is_default=False)
        previous_default = _config("id-1", is_default=True)

        db.execute = AsyncMock(
            side_effect=[_scalar_result(target), _scalar_result(previous_default)]
        )
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = anyio.run(set_default, CUSTOMER_ID, "id-2", db)
        assert result is target
        assert target.is_default is True
        assert previous_default.is_default is False

    def test_unknown_config_raises(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        with pytest.raises(ValueError):
            anyio.run(set_default, CUSTOMER_ID, "missing", db)


class TestDelete:
    def test_deleting_non_default_config_just_deletes(self):
        db = _make_mock_db()
        target = _config("id-2", is_default=False)
        db.execute = AsyncMock(return_value=_scalars_all_result([target]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        anyio.run(delete, CUSTOMER_ID, "id-2", db)
        db.delete.assert_awaited_once_with(target)

    def test_delete_default_without_replacement_deletes_and_leaves_no_default(self):
        """An AI config is never required to use the app, so deleting the
        default without naming a replacement is allowed, not rejected."""
        db = _make_mock_db()
        target = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalars_all_result([target]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        anyio.run(delete, CUSTOMER_ID, "id-1", db)
        db.delete.assert_awaited_once_with(target)

    def test_delete_default_with_named_replacement_promotes_it(self):
        db = _make_mock_db()
        target = _config("id-1", is_default=True)
        other = _config("id-2", is_default=False)
        db.execute = AsyncMock(return_value=_scalars_all_result([target, other]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        anyio.run(lambda: delete(CUSTOMER_ID, "id-1", db, new_default_id="id-2"))
        assert other.is_default is True
        db.delete.assert_awaited_once_with(target)

    def test_delete_default_with_unknown_replacement_raises(self):
        db = _make_mock_db()
        target = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalars_all_result([target]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        with pytest.raises(ValueError):
            anyio.run(lambda: delete(CUSTOMER_ID, "id-1", db, new_default_id="missing"))
        db.delete.assert_not_awaited()

    def test_delete_default_with_self_as_replacement_raises(self):
        db = _make_mock_db()
        target = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalars_all_result([target]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        with pytest.raises(ValueError):
            anyio.run(lambda: delete(CUSTOMER_ID, "id-1", db, new_default_id="id-1"))
        db.delete.assert_not_awaited()

    def test_deleting_last_remaining_config_allowed_without_replacement(self):
        db = _make_mock_db()
        target = _config("id-1", is_default=True)
        db.execute = AsyncMock(return_value=_scalars_all_result([target]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        anyio.run(delete, CUSTOMER_ID, "id-1", db)
        db.delete.assert_awaited_once_with(target)

    def test_no_op_when_no_row(self):
        db = _make_mock_db()
        db.execute = AsyncMock(return_value=_scalars_all_result([]))
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        anyio.run(delete, CUSTOMER_ID, "missing", db)
        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()
