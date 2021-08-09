from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.repositories.base import BaseRepository
from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService


class WorkspaceServiceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.deleted = false AND c.workspaceId = "{workspace_id}"'
        workspace_services = self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)
