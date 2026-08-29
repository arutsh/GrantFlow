"""Regression tests: batch lookups must accept uuid.UUID ids, not just str."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.user_client import get_customers_by_ids, get_users_by_ids


@pytest.mark.anyio
async def test_get_users_by_ids_serializes_uuid_objects():
    user_id = uuid.uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": str(user_id), "first_name": "Alice"}]

    with patch("app.services.user_client._client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await get_users_by_ids([user_id], "token")

    assert result == {str(user_id): {"id": str(user_id), "first_name": "Alice"}}
    assert mock_client.post.call_args.kwargs["json"] == [str(user_id)]


@pytest.mark.anyio
async def test_get_customers_by_ids_serializes_uuid_objects():
    customer_id = uuid.uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": str(customer_id), "name": "Test NGO"}]

    with patch("app.services.user_client._client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await get_customers_by_ids([customer_id], "token")

    assert result == {str(customer_id): {"id": str(customer_id), "name": "Test NGO"}}
    assert mock_client.post.call_args.kwargs["json"] == [str(customer_id)]
