from azure.cosmos import CosmosClient
from db.repositories.resources import ResourceRepository


class AirlockRequestRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)
