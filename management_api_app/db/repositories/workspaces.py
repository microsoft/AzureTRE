import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as, UUID4

from core import config
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate
from resources import strings
from db.errors import EntityDoesNotExist
from models.domain.workspace import Workspace
from db.repositories.base import BaseRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.schemas.workspace import WorkspaceInCreate
from db.repositories.resource_templates import ResourceTemplateRepository
from services.concatjsonschema import enrich_workspace_schema_defs
from db.repositories.templates import TemplateRepository
from services.concatjsonschema import enrich_workspace_schema_defs, enrich_workspace_service_schema_defs
from jsonschema import validate
from services.authentication import extract_auth_information


class WorkspaceRepository(BaseRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client, config.STATE_STORE_RESOURCES_CONTAINER)

    @staticmethod
    def _active_workspaces_query():
        return 'SELECT * FROM c WHERE c.isDeleted = false'

    def _get_current_workspace_template(self, template_name) -> ResourceTemplate:
        workspace_template_repo = ResourceTemplateRepository(self._client)
        template = workspace_template_repo.get_current_resource_template_by_name(template_name)
        return enrich_workspace_schema_defs(template)

    def _get_current_service_template(self, template_name) -> ResourceTemplate:
        workspace_template_repo = TemplateRepository(self._client)
        template = workspace_template_repo.get_current_workspace_template_by_name(template_name, ResourceType.WorkspaceService)
        return enrich_workspace_service_schema_defs(template)

    @staticmethod
    def _validate_workspace_parameters(workspace_create, workspace_template):
        validate(instance=workspace_create["properties"], schema=workspace_template)

    def get_all_active_workspaces(self) -> List[Workspace]:
        query = self._active_workspaces_query()
        workspaces = self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    def get_workspace_by_workspace_id(self, workspace_id: UUID4) -> Workspace:
        query = self._active_workspaces_query() + f' AND c.id="{workspace_id}"'
        workspaces = self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return parse_obj_as(Workspace, workspaces[0])

    def get_workspace_dict_by_workspace_id(self, workspace_id: UUID4) -> dict:
        query = self._active_workspaces_query() + f' AND c.id="{workspace_id}"'
        workspaces = self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return workspaces[0]

    def create_workspace_item(self, workspace_create: WorkspaceInCreate) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_template(workspace_create.workspaceType, ResourceType.Workspace)
            template_version = current_template["version"]
        except EntityDoesNotExist:
            raise ValueError(f"The workspace type '{workspace_create.workspaceType}' does not exist")

        self._validate_workspace_parameters(workspace_create.dict(), current_template)
        auth_info = extract_auth_information(workspace_create.properties["app_id"])

        # system generated parameters
        resource_spec_parameters = {
            "azure_location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        # user provided parameters
        resource_spec_parameters.update(workspace_create.properties)

        workspace = Workspace(
            id=full_workspace_id,
            displayName=workspace_create.properties["display_name"],
            description=workspace_create.properties["description"],
            resourceTemplateName=workspace_create.workspaceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE),
            authInformation=auth_info
        )

        return workspace

    def create_workspace_service_item(self, workspace_create: WorkspaceServiceInCreate, workspace_id: str) -> WorkspaceService:
        full_workspace_service_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_service_template(workspace_create.workspaceServiceType)
            template_version = current_template["version"]
        except EntityDoesNotExist:
            raise ValueError(f"The workspace type '{workspace_create.workspaceServiceType}' does not exist")

        self._validate_workspace_parameters(workspace_create.dict(), current_template)

        workspace = WorkspaceService(
            id=full_workspace_service_id,
            workspaceId=workspace_id,
            displayName=workspace_create.properties["display_name"],
            description=workspace_create.properties["description"],
            resourceTemplateName=workspace_create.workspaceServiceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=workspace_create.properties,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE),
        )

        return workspace

    def save_workspace(self, workspace: Workspace):
        self.create_item(workspace)

    def update_workspace(self, workspace: Workspace):
        self.container.upsert_item(body=workspace.dict())

    def update_resource_dict(self, resource_dict: dict):
        self.container.upsert_item(body=resource_dict)
