import uuid
from typing import List

from azure.cosmos import ContainerProxy, CosmosClient
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.query_builder import QueryBuilder
from db.repositories.base import BaseRepository
from models.domain.resource import Parameter, ResourceSpec, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @property
    def container(self) -> ContainerProxy:
        return self._container

    def get_all_active_workspaces(self) -> List[Workspace]:
        query = QueryBuilder().select_active_resources(ResourceType.Workspace).build()
        workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return workspaces

    def get_workspace_by_workspace_id(self, workspace_id: UUID4) -> Workspace:
        query = QueryBuilder().select_active_resources(ResourceType.Workspace).with_id(workspace_id).build()
        workspaces = list(self.container.query_items(query=query, enable_cross_partition_query=True))

        if workspaces:
            return workspaces[0]
        else:
            raise EntityDoesNotExist

    def create_workspace(self, workspace_create: WorkspaceInCreate) -> Workspace:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            friendlyName=workspace_create.friendlyName,
            description=workspace_create.description,
            resourceSpec=ResourceSpec(
                name=workspace_create.workspaceType,
                version="0.1.0",    # TODO: Calculate latest - Issue #167
                parameters=[
                    Parameter(name="location", value=config.RESOURCE_LOCATION),
                    Parameter(name="workspace_id", value="0001"),   # TODO: Calculate this value - Issue #166
                    Parameter(name="core_id", value=config.CORE_ID),
                    Parameter(name="address_space", value="10.2.1.0/24"),   # TODO: Calculate this value - Issue #52
                ]),
        )
        self.container.create_item(body=workspace.dict())
        return workspace
