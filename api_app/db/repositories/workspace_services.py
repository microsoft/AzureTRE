import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from db.repositories.resources import ResourceRepository
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate, WorkspaceServicePatchEnabled
from resources import strings
from db.errors import ResourceIsNotDeployed, EntityDoesNotExist
from models.domain.resource import Deployment, Status, ResourceType


class WorkspaceServiceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def active_workspace_services_query(workspace_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.deployment.status != "{Status.Deleted}" AND c.workspaceId = "{workspace_id}"'

    def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = WorkspaceServiceRepository.active_workspace_services_query(workspace_id)
        workspace_services = self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)

    def get_deployed_workspace_service_by_id(self, workspace_id: str, service_id: str) -> WorkspaceService:
        workspace_service = self.get_workspace_service_by_id(workspace_id, service_id)

        if workspace_service.deployment.status != Status.Deployed:
            raise ResourceIsNotDeployed

        return workspace_service

    def get_workspace_service_by_id(self, workspace_id: str, service_id: str) -> WorkspaceService:
        query = self.active_workspace_services_query(workspace_id) + f' AND c.id = "{service_id}"'
        workspace_services = self.query(query=query)
        if not workspace_services:
            raise EntityDoesNotExist
        return parse_obj_as(WorkspaceService, workspace_services[0])

    def get_workspace_service_spec_params(self):
        return self.get_resource_base_spec_params()

    def create_workspace_service_item(self, workspace_service_input: WorkspaceServiceInCreate, workspace_id: str) -> WorkspaceService:
        full_workspace_service_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(workspace_service_input.templateName, workspace_service_input, ResourceType.WorkspaceService)

        # we don't want something in the input to overwrite the system parameters, so dict.update can't work.
        resource_spec_parameters = {**workspace_service_input.properties, **self.get_workspace_service_spec_params()}

        workspace_service = WorkspaceService(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            templateName=workspace_service_input.templateName,
            templateVersion=template_version,
            properties=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE)
        )

        return workspace_service

    def patch_workspace_service(self, workspace_service: WorkspaceService, workspace_service_patch: WorkspaceServicePatchEnabled):
        workspace_service.properties["enabled"] = workspace_service_patch.enabled
        self.update_item(workspace_service)
