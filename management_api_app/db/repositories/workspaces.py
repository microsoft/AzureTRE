import uuid
from typing import List

from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey

from core.config import STATE_STORE_RESOURCES_CONTAINER
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import Resource, ResourceType, Status
from models.schemas.resource import ResourceInCreate
from resources import strings


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)
        if self.database:
            self._container = self.database.create_container_if_not_exists(id=STATE_STORE_RESOURCES_CONTAINER, partition_key=PartitionKey(path="/appId"))
        else:
            self._container = None

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def get_all_active_workspaces(self) -> List[Resource]:
        workspaces = []
        if self.container:
            query = f'SELECT * from c ' \
                    f'WHERE c.resourceType = "{strings.RESOURCE_TYPE_WORKSPACE}" ' \
                    f'AND c.isDeleted = false'
            workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return workspaces

    def get_workspace_by_workspace_id(self, workspace_id: str) -> Resource:
        workspaces = []
        if self.container:
            query = f'SELECT * from c ' \
                    f'WHERE c.resourceType = "{strings.RESOURCE_TYPE_WORKSPACE}" ' \
                    f'AND c.isDeleted = false ' \
                    f'AND c.id = "{workspace_id}"'
            workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        if workspaces:
            return workspaces[0]
        raise EntityDoesNotExist

    def create_workspace(self, workspace_create: ResourceInCreate) -> Resource:
        workspace = []
        if self.container:
            workspace = Resource(
                id=str(uuid.uuid4()),
                resource_name=workspace_create.name,
                resource_version=workspace_create.version,
                resource_parameters=workspace_create.parameters,
                resourceType=ResourceType.Workspace,
                status=Status.NotDeployed
            )
            self.container.create_item(body=workspace.dict())

        return workspace
