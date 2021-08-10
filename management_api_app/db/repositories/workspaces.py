import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as, UUID4

from core import config
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.resource_template import ResourceTemplate
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspacePatchEnabled
from resources import strings
from services.authentication import extract_auth_information
from services.concatjsonschema import enrich_workspace_schema_defs


class WorkspaceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def _active_workspaces_query():
        return 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.deleted = false'

    def _get_current_workspace_template(self, template_name) -> ResourceTemplate:
        workspace_template_repo = ResourceTemplateRepository(self._client)
        template = workspace_template_repo.get_current_resource_template_by_name(template_name, ResourceType.Workspace)
        return enrich_workspace_schema_defs(template)

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

    def create_workspace_item(self, workspace_create: WorkspaceInCreate) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        try:
            current_template = self._get_current_workspace_template(workspace_create.workspaceType)
            template_version = current_template["version"]
        except EntityDoesNotExist:
            raise ValueError(f"The workspace type '{workspace_create.workspaceType}' does not exist")

        self._validate_resource_parameters(workspace_create.dict(), current_template)
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
            resourceTemplateName=workspace_create.workspaceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE),
            authInformation=auth_info
        )

        return workspace

    def save_workspace(self, workspace: Workspace):
        self.create_item(workspace)

    def update_workspace(self, workspace: Workspace):
        self.container.upsert_item(body=workspace.dict())

    def patch_workspace(self, workspace: Workspace, workspace_patch: WorkspacePatchEnabled):
        workspace.resourceTemplateParameters["enabled"] = workspace_patch.enabled
        self.container.upsert_item(body=workspace.dict())
