import uuid
from typing import List

from azure.cosmos import ContainerProxy, CosmosClient
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.query_builder import QueryBuilder
from db.repositories.base import BaseRepository
from models.domain.resource import ResourceType
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
        resource_spec_parameters = {
            "location": config.RESOURCE_LOCATION,
            "workspace_id": "0001",         # TODO: Calculate this value - Issue #166
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        workspace = Workspace(
            id=str(uuid.uuid4()),
            displayName=workspace_create.displayName,
            description=workspace_create.description,
            resourceSpecName=workspace_create.workspaceType,
            resourceSpecVersion="0.1.0",    # TODO: Calculate latest - Issue #167
            resourceSpecParameters=resource_spec_parameters
        )

        self.container.create_item(body=workspace.dict())
        return workspace
