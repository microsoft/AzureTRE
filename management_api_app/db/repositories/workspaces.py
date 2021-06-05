import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.base import BaseRepository
from models.domain.resource import Status
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    def get_all_active_workspaces(self) -> List[Workspace]:
        query = 'SELECT * FROM c ' \
                'WHERE c.resourceType = "workspace" ' \
                'AND c.isDeleted = false'
        return self._query(query=query)

    def get_workspace_by_workspace_id(self, workspace_id: UUID4) -> Workspace:

        query = f'SELECT * FROM c ' \
                f'WHERE c.resourceType = "workspace" ' \
                f'AND c.isDeleted = false ' \
                f'AND c.id="{workspace_id}"'
        workspaces = self._query(query=query)
        if len(workspaces) != 1:
            raise EntityDoesNotExist
        return workspaces[0]

    @staticmethod
    def create_workspace_item(workspace_create: WorkspaceInCreate) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        resource_spec_parameters = {
            "location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        workspace = Workspace(
            id=full_workspace_id,
            displayName=workspace_create.displayName,
            description=workspace_create.description,
            resourceSpecName=workspace_create.workspaceType,
            resourceSpecVersion="0.1.0",    # TODO: Calculate latest - Issue #167
            resourceSpecParameters=resource_spec_parameters,
            status=Status.NotDeployed
        )

        return workspace

    def save_workspace(self, workspace: Workspace):
        self._create_item(workspace)
