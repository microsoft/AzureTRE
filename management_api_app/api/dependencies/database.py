from typing import Callable, Type

from azure.cosmos import CosmosClient
from fastapi import Depends, HTTPException
from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources import strings


def _get_db_client(request: Request) -> CosmosClient:
    return request.app.state.cosmos_client


def get_repository(repo_type: Type[BaseRepository]) -> Callable[[CosmosClient], BaseRepository]:
    def _get_repo(client: CosmosClient = Depends(_get_db_client)) -> BaseRepository:
        try:
            return repo_type(client)
        except UnableToAccessDatabase:
            raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    return _get_repo
