from ast import List
from uuid import uuid4
from azure.cosmos.aio import CosmosClient
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from core import config
from models.domain.resource import Resource, ResourceHistoryItem
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pydantic import parse_obj_as


class ResourceHistoryRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = ResourceHistoryRepository()
        await super().create(client, config.STATE_STORE_RESOURCES_HISTORY_CONTAINER)
        return cls

    async def get_resource_history_by_id(self, historyItemId: uuid4) -> List[ResourceHistoryItem]:
        try:
            resource_history_items = await self.read_item_by_id(str(historyItemId))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return parse_obj_as(List[ResourceHistoryItem], resource_history_items)

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
