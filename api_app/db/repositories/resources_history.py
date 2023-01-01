from typing import List
import uuid
from azure.cosmos.aio import CosmosClient
from db.repositories.base import BaseRepository
from core import config
from models.domain.resource import Resource, NewResourceHistoryItem
from pydantic import parse_obj_as


class ResourceHistoryRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = ResourceHistoryRepository()
        await super().create(client, config.STATE_STORE_RESOURCES_HISTORY_CONTAINER)
        return cls

    @staticmethod
    def resource_history_query(resourceId: str):
        return f'SELECT * FROM c WHERE c.resourceId = "{resourceId}"'

    @staticmethod
    def resource_history_with_resource_version_query(resourceId: str, resourceVersion: str):
        return f'SELECT * FROM c WHERE c.resourceId = "{resourceId}" AND c.resourceVersion = "{resourceVersion}"'

    async def get_resource_history_by_resource_id(self, resourceId: str) -> List[NewResourceHistoryItem]:
        query = self.resource_history_query(resourceId)
        resource_history_items = await self.query(query=query)
        return parse_obj_as(List[NewResourceHistoryItem], resource_history_items)

    async def create_resource_history_item(self, resource: Resource) -> NewResourceHistoryItem:
        resource_history_item_id = str(uuid.uuid4())
        resource_history_item = NewResourceHistoryItem(
            id=resource_history_item_id,
            resourceId=resource.id,
            isEnabled=resource.isEnabled,
            properties=resource.properties,
            resourceVersion=resource.resourceVersion,
            updatedWhen=resource.updatedWhen,
            user=resource.user,
            templateVersion=resource.templateVersion
        )
        # Check if already save this resourceVersion in history container
        existing_resource_history_item = await self.query(self.resource_history_with_resource_version_query(resource.id, resource.resourceVersion))
        if not existing_resource_history_item:
            await self.save_item(resource_history_item)
        return resource_history_item
