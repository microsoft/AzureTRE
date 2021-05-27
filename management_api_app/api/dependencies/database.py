from typing import Callable, Type

from azure.cosmos import CosmosClient
from fastapi import Depends
from starlette.requests import Request

from db.repositories.base import BaseRepository


def _get_db_client(request: Request) -> CosmosClient:
    return request.app.state.cosmos_client


def get_repository(repo_type: Type[BaseRepository]) -> Callable[[CosmosClient], BaseRepository]:
    def _get_repo(client: CosmosClient = Depends(_get_db_client)) -> BaseRepository:
        return repo_type(client)

    return _get_repo
