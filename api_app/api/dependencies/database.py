from typing import Callable, Type

from azure.cosmos.aio import CosmosClient
from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient
from fastapi import Depends, FastAPI, HTTPException, Request, status
from core.config import MANAGED_IDENTITY_CLIENT_ID, STATE_STORE_ENDPOINT, STATE_STORE_KEY, STATE_STORE_SSL_VERIFY, SUBSCRIPTION_ID, RESOURCE_MANAGER_ENDPOINT, CREDENTIAL_SCOPES, RESOURCE_GROUP_NAME, COSMOSDB_ACCOUNT_NAME
from core.credentials import get_credential_async
from db.errors import UnableToAccessDatabase
from db.repositories.base import BaseRepository
from resources import strings
from services.logging import logger


async def connect_to_db() -> CosmosClient:
    logger.debug(f"Connecting to {STATE_STORE_ENDPOINT}")

    async with get_credential_async() as credential:
        if MANAGED_IDENTITY_CLIENT_ID:
            logger.debug("Connecting with managed identity")
            cosmos_client = CosmosClient(
                url=STATE_STORE_ENDPOINT,
                credential=credential
            )
        else:
            logger.debug("Connecting with key")
            primary_master_key = await get_store_key(credential)

            if STATE_STORE_SSL_VERIFY:
                logger.debug("Connecting with SSL verification")
                cosmos_client = CosmosClient(
                    url=STATE_STORE_ENDPOINT, credential=primary_master_key
                )
            else:
                logger.debug("Connecting without SSL verification")
                # ignore TLS (setup is a pain) when using local Cosmos emulator.
                cosmos_client = CosmosClient(
                    STATE_STORE_ENDPOINT, primary_master_key, connection_verify=False
                )
    logger.debug("Connection established")
    return cosmos_client


async def get_store_key(credential) -> str:
    logger.debug("Getting store key")
    if STATE_STORE_KEY:
        primary_master_key = STATE_STORE_KEY
    else:
        async with CosmosDBManagementClient(
            credential,
            subscription_id=SUBSCRIPTION_ID,
            base_url=RESOURCE_MANAGER_ENDPOINT,
            credential_scopes=CREDENTIAL_SCOPES
        ) as cosmosdb_mng_client:
            database_keys = await cosmosdb_mng_client.database_accounts.list_keys(
                resource_group_name=RESOURCE_GROUP_NAME,
                account_name=COSMOSDB_ACCOUNT_NAME,
            )
            primary_master_key = database_keys.primary_master_key

    return primary_master_key


async def get_db_client(app: FastAPI) -> CosmosClient:
    logger.debug("Getting cosmos client")
    cosmos_client = None
    if hasattr(app.state, 'cosmos_client') and app.state.cosmos_client:
        logger.debug("Cosmos client found in state")
        cosmos_client = app.state.cosmos_client
        # TODO: if session is closed recreate - need to investigate why this is happening
        # https://github.com/Azure/azure-sdk-for-python/issues/32309
        if hasattr(cosmos_client.client_connection, "session") and not cosmos_client.client_connection.session:
            logger.debug("Cosmos client session is None")
            cosmos_client = await connect_to_db()
    else:
        logger.debug("No cosmos client found, creating one")
        cosmos_client = await connect_to_db()

    app.state.cosmos_client = cosmos_client
    return app.state.cosmos_client


async def get_db_client_from_request(request: Request) -> CosmosClient:
    return await get_db_client(request.app)


def get_repository(
    repo_type: Type[BaseRepository],
) -> Callable[[CosmosClient], BaseRepository]:
    async def _get_repo(
        client: CosmosClient = Depends(get_db_client_from_request),
    ) -> BaseRepository:
        try:
            return await repo_type.create(client)
        except UnableToAccessDatabase:
            logger.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=strings.STATE_STORE_ENDPOINT_NOT_RESPONDING,
            )

    return _get_repo
