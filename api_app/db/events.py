from azure.cosmos.aio import CosmosClient

from api.dependencies.database import get_db_client
from db.repositories.resources import ResourceRepository
from services.logging import logger


async def bootstrap_database(app) -> bool:
    try:
        client: CosmosClient = await get_db_client(app)
        if client:
            # Test access to database
            await ResourceRepository.create(client)
            return True
    except Exception as e:
        logger.exception("Could not bootstrap database")
        logger.debug(e)
        return False
