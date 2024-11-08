import pytest
from mock import patch
from fastapi import HTTPException

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from api.helpers import get_repository

pytestmark = pytest.mark.asyncio


@patch("db.repositories.base.BaseRepository.create")
async def test_get_repository_raises_http_exception_when_unable_to_access_database(create_base_repo_mock):
    create_base_repo_mock.side_effect = UnableToAccessDatabase()
    with pytest.raises(HTTPException):
        get_repo = get_repository(BaseRepository)
        await get_repo()
