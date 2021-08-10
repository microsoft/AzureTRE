import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from db.repositories.resources import ResourceRepository
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate
from resources import strings
from db.errors import EntityDoesNotExist
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.resource_template import ResourceTemplate
from db.repositories.resource_templates import ResourceTemplateRepository
from services.concatjsonschema import enrich_workspace_service_schema_defs


class WorkspaceServiceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def get_active_workspace_services_for_workspace(self, workspace_id: str) -> List[WorkspaceService]:
        """
        returns list of "non-deleted" workspace services linked to this workspace
        """
        query = f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.WorkspaceService}" AND c.deleted = false AND c.workspaceId = "{workspace_id}"'
        workspace_services = self.query(query=query)
        return parse_obj_as(List[WorkspaceService], workspace_services)

    def _get_current_workspace_service_template(self, template_name) -> ResourceTemplate:
        resource_template_repo = ResourceTemplateRepository(self._client)
        template = resource_template_repo.get_current_resource_template_by_name(template_name, ResourceType.WorkspaceService)
        return enrich_workspace_service_schema_defs(template)

    def create_workspace_service_item(self, workspace_service_create: WorkspaceServiceInCreate, workspace_id: str) -> WorkspaceService:
        full_workspace_service_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_workspace_service_template(workspace_service_create.workspaceServiceType)
            template_version = current_template["version"]
        except EntityDoesNotExist:
            raise ValueError(f"The workspace service type '{workspace_service_create.workspaceServiceType}' does not exist")

        self._validate_resource_parameters(workspace_service_create.dict(), current_template)

        workspace_service = WorkspaceService(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            displayName=workspace_service_create.properties["display_name"],
            description=workspace_service_create.properties["description"],
            resourceTemplateName=workspace_service_create.workspaceServiceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=workspace_service_create.properties,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE)
        )

        return workspace_service

    def save_workspace_service(self, workspace_service: WorkspaceService):
        self.create_item(workspace_service)
