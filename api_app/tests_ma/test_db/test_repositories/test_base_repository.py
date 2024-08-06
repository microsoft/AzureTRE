import pytest
from mock import patch

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository

pytestmark = pytest.mark.asyncio


@patch("api.dependencies.database.Database.get_container_proxy")
async def test_instantiating_a_repo_raises_unable_to_access_database_if_database_cant_be_accessed(get_container_proxy_mock):
    get_container_proxy_mock.side_effect = Exception()
    with pytest.raises(UnableToAccessDatabase):
        await BaseRepository.create()
