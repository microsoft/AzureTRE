import logging
from typing import Callable, Type

from azure.cosmos import CosmosClient
from fastapi import Depends, FastAPI, HTTPException
from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from core import config
from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources import strings


def connect_to_db() -> CosmosClient:
    logging.debug(f"Connecting to {config.STATE_STORE_ENDPOINT}")

    try:
        if config.DEBUG:
            # ignore TLS(setup is pain) when on dev container and connecting to cosmosdb on windows host.
            cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, config.STATE_STORE_KEY,
                                         connection_verify=False)
        else:
            cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, config.STATE_STORE_KEY)
        logging.debug("Connection established")
        return cosmos_client
    except Exception as e:
        logging.debug(f"Connection to state store could not be established: {e}")


def get_db_client(app: FastAPI) -> CosmosClient:
    if not app.state.cosmos_client:
        app.state.cosmos_client = connect_to_db()
    return app.state.cosmos_client


def get_db_client_from_request(request: Request) -> CosmosClient:
    return get_db_client(request.app)


def get_repository(repo_type: Type[BaseRepository]) -> Callable[[CosmosClient], BaseRepository]:
    def _get_repo(client: CosmosClient = Depends(get_db_client_from_request)) -> BaseRepository:
        try:
            return repo_type(client)
        except UnableToAccessDatabase:
            raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    return _get_repo
