from azure.cosmos.aio import CosmosClient
from db.repositories.base import BaseRepository
from core import config
from models.domain.resource import Resource, ResourceHistoryItem


class ResourceHistoryRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = ResourceHistoryRepository()
        await super().create(client, config.STATE_STORE_RESOURCES_HISTORY_CONTAINER)
        return cls

    async def create_resource_history_item(self, resource: Resource) -> ResourceHistoryItem:
        resource_history_item = ResourceHistoryItem(
            resourceId=resource.id,
            isEnabled=resource.isEnabled,
            properties=resource.properties,
            resourceVersion=resource.resourceVersion,
            updatedWhen=resource.updatedWhen,
            user=resource.user,
            templateVersion=resource.templateVersion
        )
        await self.save_item(resource_history_item)
        return resource_history_item
