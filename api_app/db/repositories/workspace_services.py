import uuid
from typing import List, Tuple

from pydantic import parse_obj_as
from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.resource_template import ResourceTemplate
from models.domain.authentication import User
from db.repositories.resource_templates import ResourceTemplateRepository

import resources.strings as strings
from db.repositories.resources import ResourceRepository, IS_NOT_DELETED_CLAUSE
from db.repositories.operations import OperationRepository
from models.domain.workspace_service import WorkspaceService
from models.schemas.resource import ResourcePatch
from models.schemas.workspace_service import WorkspaceServiceInCreate
from db.errors import ResourceIsNotDeployed, EntityDoesNotExist
from models.domain.resource import ResourceType


class WorkspaceServiceRepository(ResourceRepository):
    @classmethod
    async def create(cls):
        cls = WorkspaceServiceRepository()
        await super().create()
        return cls

    @staticmethod
    def workspace_services_query(workspace_id: str):
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.workspaceId = "{workspace_id}"'

    @staticmethod
    def active_workspace_services_query(workspace_id: str):
        return f'SELECT * FROM c WHERE {IS_NOT_DELETED_CLAUSE} AND c.resourceType = "{ResourceType.WorkspaceService}" AND c.workspaceId = "{workspace_id}"'

    async def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = WorkspaceServiceRepository.active_workspace_services_query(workspace_id)
        workspace_services = await self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)

    async def get_deployed_workspace_service_by_id(self, workspace_id: str, service_id: str, operations_repo: OperationRepository) -> WorkspaceService:
        workspace_service = await self.get_workspace_service_by_id(workspace_id, service_id)

        if (not await operations_repo.resource_has_deployed_operation(resource_id=service_id)):
            raise ResourceIsNotDeployed

        return workspace_service

    async def get_workspace_service_by_id(self, workspace_id: str, service_id: str) -> WorkspaceService:
        query = self.workspace_services_query(workspace_id) + f' AND c.id = "{service_id}"'
        workspace_services = await self.query(query=query)
        if not workspace_services:
            raise EntityDoesNotExist
        return parse_obj_as(WorkspaceService, workspace_services[0])

    def get_workspace_service_spec_params(self):
        return self.get_resource_base_spec_params()

    async def create_workspace_service_item(self, workspace_service_input: WorkspaceServiceInCreate, workspace_id: str, user_roles=List[str]) -> Tuple[WorkspaceService, ResourceTemplate]:
        full_workspace_service_id = str(uuid.uuid4())

        template = await self.validate_input_against_template(workspace_service_input.templateName, workspace_service_input, ResourceType.WorkspaceService, user_roles)

        # we don't want something in the input to overwrite the system parameters, so dict.update can't work.
        resource_spec_parameters = {**workspace_service_input.properties, **self.get_workspace_service_spec_params()}

        workspace_service = WorkspaceService(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            templateName=workspace_service_input.templateName,
            templateVersion=template.version,
            properties=resource_spec_parameters,
            resourcePath=f'/workspaces/{workspace_id}/workspace-services/{full_workspace_service_id}',
            etag=''
        )

        return workspace_service, template

    async def patch_workspace_service(self, workspace_service: WorkspaceService, workspace_service_patch: ResourcePatch, etag: str, resource_template_repo: ResourceTemplateRepository, resource_history_repo: ResourceHistoryRepository, user: User, force_version_update: bool) -> Tuple[WorkspaceService, ResourceTemplate]:
        # get workspace service template
        workspace_service_template = await resource_template_repo.get_template_by_name_and_version(workspace_service.templateName, workspace_service.templateVersion, ResourceType.WorkspaceService)
        return await self.patch_resource(workspace_service, workspace_service_patch, workspace_service_template, etag, resource_template_repo, resource_history_repo, user, strings.RESOURCE_ACTION_UPDATE, force_version_update)
