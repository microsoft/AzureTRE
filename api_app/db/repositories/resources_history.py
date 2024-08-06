from typing import List
import uuid
from pydantic import parse_obj_as

from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from core import config
from models.domain.resource import Resource, ResourceHistoryItem
from services.logging import logger


class ResourceHistoryRepository(BaseRepository):
    @classmethod
    async def create(cls):
        cls = ResourceHistoryRepository()
        await super().create(config.STATE_STORE_RESOURCES_HISTORY_CONTAINER)
        return cls

    @staticmethod
    def is_valid_uuid(resourceId):
        try:
            uuid.UUID(str(resourceId))
        except ValueError:
            raise ValueError("Resource Id should be a valid GUID")

    def resource_history_query(self, resourceId: str):
        logger.debug("Validate sanity of resourceId")
        self.is_valid_uuid(resourceId)
        return f'SELECT * FROM c WHERE c.resourceId = "{resourceId}"'

    async def get_resource_history_by_resource_id(self, resource_id: str) -> List[ResourceHistoryItem]:
        query = self.resource_history_query(resource_id)
        try:
            logger.info(f"Fetching history for resource {resource_id}")
            resource_history_items = await self.query(query=query)
            logger.debug(f"Got {len(resource_history_items)} history items for resource {resource_id}")
        except EntityDoesNotExist:
            logger.info(f"No history for resource {resource_id}")
            resource_history_items = []
        return parse_obj_as(List[ResourceHistoryItem], resource_history_items)

    async def create_resource_history_item(self, resource: Resource) -> ResourceHistoryItem:
        logger.info(f"Creating a new history item for resource {resource.id}")
        resource_history_item_id = str(uuid.uuid4())
        resource_history_item = ResourceHistoryItem(
            id=resource_history_item_id,
            resourceId=resource.id,
            isEnabled=resource.isEnabled,
            properties=resource.properties,
            resourceVersion=resource.resourceVersion,
            updatedWhen=resource.updatedWhen,
            user=resource.user,
            templateVersion=resource.templateVersion
        )
        logger.info(f"Saving history item for {resource.id}")
        try:
            await self.save_item(resource_history_item)
        except Exception:
            logger.exception(f"Failed saving history item for {resource.id}")
            raise
        return resource_history_item
