from azure.cosmos.aio import CosmosClient
from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient

from core.config import MANAGED_IDENTITY_CLIENT_ID, STATE_STORE_ENDPOINT, STATE_STORE_KEY, STATE_STORE_SSL_VERIFY, SUBSCRIPTION_ID, RESOURCE_MANAGER_ENDPOINT, CREDENTIAL_SCOPES, RESOURCE_GROUP_NAME, COSMOSDB_ACCOUNT_NAME
from core.credentials import get_credential_async
from services.logging import logger


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Database(metaclass=Singleton):
    cosmos_client = None

    def __init__(self):
        pass

    @classmethod
    async def _connect_to_db(self) -> CosmosClient:
        logger.debug(f"Connecting to {STATE_STORE_ENDPOINT}")

        credential = await get_credential_async()
        if MANAGED_IDENTITY_CLIENT_ID:
            logger.debug("Connecting with managed identity")
            cosmos_client = CosmosClient(
                url=STATE_STORE_ENDPOINT,
                credential=credential
            )
        else:
            logger.debug("Connecting with key")
            primary_master_key = await self._get_store_key(credential)

            if STATE_STORE_SSL_VERIFY:
                logger.debug("Connecting with SSL verification")
                cosmos_client = CosmosClient(
                    url=STATE_STORE_ENDPOINT,
                    credential=primary_master_key
                )
            else:
                logger.debug("Connecting without SSL verification")
                # ignore TLS (setup is a pain) when using local Cosmos emulator.
                cosmos_client = CosmosClient(
                    url=STATE_STORE_ENDPOINT,
                    credential=primary_master_key,
                    connection_verify=False
                )
        logger.debug("Connection established")
        return cosmos_client

    @classmethod
    async def _get_store_key(self, credential) -> str:
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

    @classmethod
    async def get_db_client(self) -> CosmosClient:
        logger.debug("Getting cosmos client")
        if not Database.cosmos_client:
            Database.cosmos_client = await self._connect_to_db()
        return self.cosmos_client
