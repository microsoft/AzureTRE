from typing import Callable, Type

from azure.cosmos import DatabaseProxy
from fastapi import Depends
from starlette.requests import Request

from db.repositories.base import BaseRepository


def _get_db_client(request: Request) -> DatabaseProxy:
    return request.app.state.state_database


def get_repository(repo_type: Type[BaseRepository]) -> Callable[[DatabaseProxy], BaseRepository]:
    def _get_repo(database: DatabaseProxy = Depends(_get_db_client)) -> BaseRepository:
        return repo_type(database)

    return _get_repo
