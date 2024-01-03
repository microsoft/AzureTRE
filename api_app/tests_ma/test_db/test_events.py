from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import AzureError
import pytest
from db import events

pytestmark = pytest.mark.asyncio


@patch("db.events.get_credential")
@patch("db.events.CosmosDBManagementClient")
async def test_bootstrap_database_success(cosmos_db_mgmt_client_mock, get_credential_async_context_mock):
    get_credential_async_context_mock.return_value = AsyncMock()
    cosmos_db_mgmt_client_mock.return_value = MagicMock()

    result = await events.bootstrap_database()

    assert result is True


@patch("db.events.get_credential")
@patch("db.events.CosmosDBManagementClient")
async def test_bootstrap_database_failure(cosmos_db_mgmt_client_mock, get_credential_async_context_mock):
    get_credential_async_context_mock.return_value = AsyncMock()
    cosmos_db_mgmt_client_mock.side_effect = AzureError("some error")

    result = await events.bootstrap_database()

    assert result is False
