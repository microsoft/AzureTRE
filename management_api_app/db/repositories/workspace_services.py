import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from db.repositories.resources import ResourceRepository
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate
from resources import strings
from db.errors import ResourceIsNotDeployed
from models.domain.resource import Deployment, Status, ResourceType


class WorkspaceServiceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.deployment.status != "{Status.Deleted}" AND c.workspaceId = "{workspace_id}"'
        workspace_services = self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)

    def get_deployed_workspace_service_by_id(self, workspace_service_id: str) -> WorkspaceService:
        workspace_service = self.get_workspace_service_by_id(workspace_service_id)

        if workspace_service.deployment.status != Status.Deployed:
            raise ResourceIsNotDeployed

        return workspace_service

    def get_workspace_service_by_id(self, workspace_service_id: str) -> WorkspaceService:
        workspace_service = self.get_resource_dict_by_type_and_id(workspace_service_id, ResourceType.WorkspaceService)
        return parse_obj_as(WorkspaceService, workspace_service)

    def create_workspace_service_item(self, workspace_service_input: WorkspaceServiceInCreate, workspace_id: str) -> WorkspaceService:
        full_workspace_service_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(workspace_service_input.workspaceServiceType, workspace_service_input, ResourceType.WorkspaceService)

        workspace_service = WorkspaceService(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            resourceTemplateName=workspace_service_input.workspaceServiceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=workspace_service_input.properties,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE)
        )

        return workspace_service
