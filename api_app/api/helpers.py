from typing import Callable, Type

from fastapi import HTTPException, status

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources.strings import UNABLE_TO_GET_STATE_STORE_CLIENT
from services.logging import logger


def get_repository(repo_type: Type[BaseRepository],) -> Callable:
    async def _get_repo() -> BaseRepository:
        try:
            return await repo_type.create()
        except UnableToAccessDatabase:
            logger.exception(UNABLE_TO_GET_STATE_STORE_CLIENT)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=UNABLE_TO_GET_STATE_STORE_CLIENT,
            )

    return _get_repo
