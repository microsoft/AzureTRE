import logging
from typing import Callable, Type

from azure.cosmos import CosmosClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from fastapi import Depends, FastAPI, HTTPException
from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from core import config, credentials
from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources import strings


def connect_to_db() -> CosmosClient:
    logging.debug(f"Connecting to {config.STATE_STORE_ENDPOINT}")

    try:
        primary_master_key = get_store_key()

        if config.STATE_STORE_SSL_VERIFY:
            cosmos_client = CosmosClient(url=config.STATE_STORE_ENDPOINT, credential=primary_master_key, consistency_level='Session')
        else:
            # ignore TLS (setup is a pain) when using local Cosmos emulator.
            cosmos_client = CosmosClient(config.STATE_STORE_ENDPOINT, primary_master_key, consistency_level='Session', connection_verify=False)
        logging.debug("Connection established")
        return cosmos_client
    except Exception:
        logging.exception("Connection to state store could not be established.")


def get_store_key() -> str:
    if config.STATE_STORE_KEY:
        primary_master_key = config.STATE_STORE_KEY
    else:
        cosmosdb_client = CosmosDBManagementClient(credentials.get_credential(), subscription_id=config.SUBSCRIPTION_ID)
        database_keys = cosmosdb_client.database_accounts.list_keys(resource_group_name=config.RESOURCE_GROUP_NAME, account_name=config.COSMOSDB_ACCOUNT_NAME)
        primary_master_key = database_keys.primary_master_key

    return primary_master_key


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
            logging.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
            raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)

    return _get_repo
