from typing import List

from azure.cosmos import ContainerProxy, DatabaseProxy, PartitionKey

from core.config import STATE_STORE_RESOURCES_CONTAINER
from db.repositories.base import BaseRepository
from models.domain.resource import Resource
from resources import strings


class WorkspaceRepository(BaseRepository):
    def __init__(self, database: DatabaseProxy):
        super().__init__(database)
        if database:
            self._container = database.create_container_if_not_exists(id=STATE_STORE_RESOURCES_CONTAINER, partition_key=PartitionKey(path="/appId"))

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def get_all_active_resources(self) -> List[Resource]:
        workspaces = []
        if self.container:
            query = f'SELECT * from c WHERE c.resourceType = "{strings.RESOURCE_TYPE_WORKSPACE}" AND c.status != "{strings.RESOURCE_STATUS_DELETED}"'
            workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return workspaces
