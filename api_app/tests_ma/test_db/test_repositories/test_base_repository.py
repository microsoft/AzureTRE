import pytest

from mock import patch, MagicMock

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository

pytestmark = pytest.mark.asyncio


async def test_instantiating_a_repo_raises_unable_to_access_database_if_database_cant_be_accessed():
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        cosmos_client_mock.create_container_if_not_exists = MagicMock(side_effect=Exception)
        with pytest.raises(UnableToAccessDatabase):
            await BaseRepository.create("container")
