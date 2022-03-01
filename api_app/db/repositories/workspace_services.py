import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as
from db.repositories.resource_templates import ResourceTemplateRepository

from db.repositories.resources import ResourceRepository, IS_ACTIVE_CLAUSE
from db.repositories.operations import OperationRepository
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourcePatch
from models.schemas.workspace_service import WorkspaceServiceInCreate
from db.errors import ResourceIsNotDeployed, EntityDoesNotExist
from models.domain.resource import ResourceType


class WorkspaceServiceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def workspace_services_query(workspace_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.workspaceId = "{workspace_id}"'

    @staticmethod
    def active_workspace_services_query(workspace_id: str):
        return f'SELECT * FROM c WHERE {IS_ACTIVE_CLAUSE} AND c.resourceType = "{ResourceType.WorkspaceService}" AND c.workspaceId = "{workspace_id}"'

    def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = WorkspaceServiceRepository.active_workspace_services_query(workspace_id)
        workspace_services = self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)

    def get_deployed_workspace_service_by_id(self, workspace_id: str, service_id: str, operations_repo: OperationRepository) -> WorkspaceService:
        workspace_service = self.get_workspace_service_by_id(workspace_id, service_id)

        if (not operations_repo.resource_has_deployed_operation(resource_id=service_id)):
            raise ResourceIsNotDeployed

        return workspace_service

    def get_workspace_service_by_id(self, workspace_id: str, service_id: str) -> WorkspaceService:
        query = self.workspace_services_query(workspace_id) + f' AND c.id = "{service_id}"'
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
            resourcePath=f'/workspaces/{workspace_id}/workspace-services/{full_workspace_service_id}',
            etag=''
        )

        return workspace_service

    def patch_workspace_service(self, workspace_service: WorkspaceService, workspace_service_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository) -> WorkspaceService:
        # get workspace service template
        workspace_service_template = resource_template_repo.get_template_by_name_and_version(workspace_service.templateName, workspace_service.templateVersion, ResourceType.WorkspaceService)
        return self.patch_resource(workspace_service, workspace_service_patch, workspace_service_template, etag)
