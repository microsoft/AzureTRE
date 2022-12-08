import pytest

from mock import patch, AsyncMock

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository

pytestmark = pytest.mark.asyncio


@patch('azure.cosmos.CosmosClient')
async def test_instantiating_a_repo_raises_unable_to_access_database_if_database_cant_be_accessed(cosmos_client_mock):
    cosmos_client_mock.get_database_client = AsyncMock(side_effect=Exception)

    with pytest.raises(UnableToAccessDatabase):
        await BaseRepository.create(cosmos_client_mock, "container")
