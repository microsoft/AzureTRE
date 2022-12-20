import logging

from azure.cosmos.aio import CosmosClient

from api.dependencies.database import get_db_client
from core import config


async def bootstrap_database(app) -> None:
    try:
        client: CosmosClient = await get_db_client(app)
        if client:
            await client.create_database_if_not_exists(id=config.STATE_STORE_DATABASE)
    except Exception as e:
        logging.debug(e)
