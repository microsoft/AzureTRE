import uuid
from typing import List

from azure.cosmos import CosmosClient
from pydantic import parse_obj_as

from core import config
from db.errors import ResourceIsNotDeployed, EntityDoesNotExist
from db.repositories.resources import ResourceRepository, IS_ACTIVE_CLAUSE
from db.repositories.operations import OperationRepository
from models.domain.resource import ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspacePatchEnabled
from services.cidr_service import generate_new_cidr


class WorkspaceRepository(ResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    @staticmethod
    def workspaces_query_string():
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.Workspace}"'

    @staticmethod
    def active_workspaces_query_string():
        return f'SELECT * FROM c WHERE c.resourceType = "{ResourceType.Workspace}" AND {IS_ACTIVE_CLAUSE}'

    def get_active_workspaces(self) -> List[Workspace]:
        query = WorkspaceRepository.active_workspaces_query_string()
        workspaces = self.query(query=query)
        return parse_obj_as(List[Workspace], workspaces)

    def get_deployed_workspace_by_id(self, workspace_id: str, operations_repo: OperationRepository) -> Workspace:
        workspace = self.get_workspace_by_id(workspace_id)

        if (not operations_repo.resource_has_deployed_operation(resource_id=workspace_id)):
            raise ResourceIsNotDeployed

        return workspace

    def get_workspace_by_id(self, workspace_id: str) -> Workspace:
        query = self.workspaces_query_string() + f' AND c.id = "{workspace_id}"'
        workspaces = self.query(query=query)
        if not workspaces:
            raise EntityDoesNotExist
        return parse_obj_as(Workspace, workspaces[0])

    def create_workspace_item(self, workspace_input: WorkspaceInCreate, auth_info: dict) -> Workspace:
        full_workspace_id = str(uuid.uuid4())

        template_version = self.validate_input_against_template(workspace_input.templateName, workspace_input, ResourceType.Workspace)

        address_space_param = {"address_space": self.get_address_space_based_on_size(workspace_input)}

        # we don't want something in the input to overwrite the system parameters, so dict.update can't work. Priorities from right to left.
        resource_spec_parameters = {**workspace_input.properties, **address_space_param, **self.get_workspace_spec_params(full_workspace_id)}

        workspace = Workspace(
            id=full_workspace_id,
            templateName=workspace_input.templateName,
            templateVersion=template_version,
            properties=resource_spec_parameters,
            authInformation=auth_info,
            resourcePath=f'/workspaces/{full_workspace_id}'
        )

        return workspace

    def get_address_space_based_on_size(self, workspace_input):
        address_space_size = workspace_input.properties.get("address_space_size")

        if (address_space_size == "small"):
            return self.get_new_address_space(24)
        if (address_space_size == "medium"):
            return self.get_new_address_space(22)
        if (address_space_size == "large"):
            return self.get_new_address_space(16)
        if (address_space_size == "custom"):
            # if address_space isn't provided in the input, generate a new one.
            # TODO: #772 check that the provided address_space is available in the network.
            # TODO: #773 allow custom sized networks to be requested
            return workspace_input.properties.get("address_space") or self.get_new_address_space()

        # The default T-Shirt size network is small.
        return self.get_new_address_space(24)

    def get_new_address_space(self, cidr_netmask: int = 24):
        networks = [x.properties["address_space"] for x in self.get_active_workspaces()]

        new_address_space = generate_new_cidr(networks, cidr_netmask)
        return new_address_space

    def patch_workspace(self, workspace: Workspace, workspace_patch: WorkspacePatchEnabled):
        workspace.properties["enabled"] = workspace_patch.enabled
        self.update_item(workspace)

    def get_workspace_spec_params(self, full_workspace_id: str):
        params = self.get_resource_base_spec_params()
        params.update({
            "azure_location": config.RESOURCE_LOCATION,
            "workspace_id": full_workspace_id[-4:],  # TODO: remove with #729
        })
        return params
