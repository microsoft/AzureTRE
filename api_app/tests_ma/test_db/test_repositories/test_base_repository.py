import pytest

from mock import patch, MagicMock

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository


@patch('azure.cosmos.CosmosClient')
def test_instantiating_a_repo_raises_unable_to_access_database_if_database_cant_be_accessed(cosmos_client_mock):
    cosmos_client_mock.get_database_client = MagicMock(side_effect=Exception)

    with pytest.raises(UnableToAccessDatabase):
        BaseRepository(cosmos_client_mock, "container")
