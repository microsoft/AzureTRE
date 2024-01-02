from typing import Callable, Type

from fastapi import HTTPException, logger, status

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources.strings import STATE_STORE_ENDPOINT_NOT_RESPONDING


def get_repository(repo_type: Type[BaseRepository],) -> Callable:
    async def _get_repo() -> BaseRepository:
        try:
            return await repo_type.create()
        except UnableToAccessDatabase:
            logger.exception(STATE_STORE_ENDPOINT_NOT_RESPONDING)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=STATE_STORE_ENDPOINT_NOT_RESPONDING,
            )

    return _get_repo
