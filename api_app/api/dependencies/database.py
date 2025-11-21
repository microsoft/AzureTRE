from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy

from core.config import STATE_STORE_ENDPOINT, STATE_STORE_KEY, STATE_STORE_SSL_VERIFY, STATE_STORE_DATABASE
from core.credentials import get_credential_async
from services.logging import logger


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Database(metaclass=Singleton):

    _cosmos_client: CosmosClient = None
    _database_proxy: DatabaseProxy = None

    def __init__(cls):
        pass

    @classmethod
    async def _connect_to_db(cls) -> CosmosClient:
        logger.debug(f"Connecting to {STATE_STORE_ENDPOINT}")

        if STATE_STORE_KEY:
            logger.debug("Connecting with key")
            if STATE_STORE_SSL_VERIFY:
                logger.debug("Connecting with SSL verification")
                cosmos_client = CosmosClient(
                    url=STATE_STORE_ENDPOINT,
                    credential=STATE_STORE_KEY
                )
            else:
                logger.debug("Connecting without SSL verification")
                # ignore TLS (setup is a pain) when using local Cosmos emulator.
                cosmos_client = CosmosClient(
                    url=STATE_STORE_ENDPOINT,
                    credential=STATE_STORE_KEY,
                    connection_verify=False
                )
        else:
            logger.debug("Connecting with managed identity")
            credential = await get_credential_async()
            cosmos_client = CosmosClient(
                url=STATE_STORE_ENDPOINT,
                credential=credential
            )

        logger.debug("Connection established")
        return cosmos_client

    @classmethod
    async def get_container_proxy(cls, container_name) -> ContainerProxy:
        if cls._cosmos_client is None:
            cls._cosmos_client = await cls._connect_to_db()

        if cls._database_proxy is None:
            cls._database_proxy = cls._cosmos_client.get_database_client(STATE_STORE_DATABASE)

        return cls._database_proxy.get_container_client(container_name)
