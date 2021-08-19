import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.errors import ResourceIsNotDeployed
from db.repositories.resources import ResourceRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspacePatchEnabled
from resources import strings
from services.authentication import extract_auth_information


class WorkspaceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def get_active_workspaces(self) -> List[Workspace]:
        query = f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.Workspace}" AND c.deployment.status != "{Status.Deleted}"'
        workspaces = self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    def get_deployed_workspace_by_workspace_id(self, workspace_id: str) -> Workspace:
        workspace = self.get_workspace_by_workspace_id(workspace_id)

        if workspace.deployment.status != Status.Deployed:
            raise ResourceIsNotDeployed

        return workspace

    def get_workspace_by_workspace_id(self, workspace_id: str) -> Workspace:
        workspace = self.get_resource_dict_by_type_and_id(workspace_id, ResourceType.Workspace)
        return parse_obj_as(Workspace, workspace)

    def create_workspace_item(self, workspace_input: WorkspaceInCreate) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(workspace_input.workspaceType, workspace_input, ResourceType.Workspace)

        auth_info = extract_auth_information(workspace_input.properties["app_id"])

        # system generated parameters
        resource_spec_parameters = {
            "azure_location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],
            "tre_id": config.TRE_ID,
            "address_space": "10.2.1.0/24"  # TODO: Calculate this value - Issue #52
        }

        # user provided parameters
        resource_spec_parameters.update(workspace_input.properties)

        workspace = Workspace(
            id=full_workspace_id,
            resourceTemplateName=workspace_input.workspaceType,
            resourceTemplateVersion=template_version,
            resourceTemplateParameters=resource_spec_parameters,
            deployment=Deployment(status=Status.NotDeployed, message=strings.RESOURCE_STATUS_NOT_DEPLOYED_MESSAGE),
            authInformation=auth_info
        )

        return workspace

    def patch_workspace(self, workspace: Workspace, workspace_patch: WorkspacePatchEnabled):
        workspace.resourceTemplateParameters["enabled"] = workspace_patch.enabled
        self.update_item(workspace)
