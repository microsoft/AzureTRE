from azure.cosmos import CosmosClient
from core import config
from db.repositories.base import BaseRepository


class AirlockResourceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)
